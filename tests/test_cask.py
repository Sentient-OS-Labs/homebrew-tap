"""Exercise the actual scripts serialized by Homebrew, without changing host services.

Run with SENTIENT_TEST_CASK=owner/tap/sentient-os python3 tests/test_cask.py.
The named, trusted local tap must point at the checkout being tested.
"""

import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import unittest


MANAGED = "system/jesai.Sentient-OS-macOS.WakeHelper.Managed"
LEGACY = "system/jesai.Sentient-OS-macOS.WakeHelper"
PLIST = "/Library/LaunchDaemons/jesai.Sentient-OS-macOS.WakeHelper.plist"

# Every external command used by the uninstall script is replaced in the test
# copy. The production script has fixed absolute paths and no test overrides.
STUB = r'''
import json, os, pathlib, sys
state_path = pathlib.Path(os.environ["FIXTURE_STATE"])
state = json.loads(state_path.read_text())
command = pathlib.Path(sys.argv[0]).name
args = sys.argv[1:]
state["calls"].append([command, *args])
status = 0
if command == "sudo":
    state_path.write_text(json.dumps(state))
    if state.get("sudo_fail"):
        sys.exit(1)
    os.execv(args[0], args)
elif command == "launchctl":
    action, target = args
    if action == "print":
        if state.get("probe_error") or (state.get("post_probe_error") and state.get("booted")):
            status = 5
        else:
            status = 0 if target in state["services"] else 113
    elif action == "bootout":
        if not state.get("bootout_noop"):
            state["services"].remove(target)
            state["booted"] = True
        if state.get("bootout_noop") or state.get("bootout_race"):
            status = 5
    else:
        raise AssertionError(args)
elif command == "pmset":
    assert args == ["-a", "disablesleep", "0"], args
    status = 1 if state.get("restore_fail") else 0
elif command == "rm":
    assert args[:2] == ["-f", "--"], args
    assert args[2] == state["plist"], args
    if state.get("delete_fail"):
        status = 1
    else:
        pathlib.Path(args[2]).unlink(missing_ok=True)
elif command == "pgrep":
    assert args == ["-x", "Sentient OS"], args
    status = state.get("pgrep_status", 1)
    if status == 0:
        print("12345")
elif command == "ps":
    assert args == ["-p", "12345", "-o", "uid="], args
    print(state.get("process_uid", 501))
    status = state.get("ps_status", 0)
elif command == "sw_vers":
    print(state["version"])
else:
    raise AssertionError(command)
state_path.write_text(json.dumps(state))
sys.exit(status)
'''


class CaskTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        result = subprocess.run(
            ["brew", "info", "--json=v2", "--cask", os.environ["SENTIENT_TEST_CASK"]],
            env={**os.environ, "HOMEBREW_NO_AUTO_UPDATE": "1"},
            capture_output=True, text=True, check=True,
        )
        if "deprecated" in result.stderr.lower():
            raise AssertionError(result.stderr)
        cls.cask = json.loads(result.stdout)["casks"][0]
        artifacts = cls.cask["artifacts"]
        cls.uninstall = next(a["uninstall"][0] for a in artifacts if "uninstall" in a)
        cls.preflight = next(a["preflight_steps"][0]["steps"][0] for a in artifacts if "preflight_steps" in a)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="sentient-cask-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.plist = self.root / "legacy.plist"
        self.state_path = self.root / "state.json"
        self.state = {"calls": [], "services": [], "plist": str(self.plist)}
        self.replacements = {PLIST: str(self.plist)}
        for command in ["/usr/bin/sudo", "/bin/launchctl", "/usr/bin/pmset", "/bin/rm",
                        "/usr/bin/pgrep", "/bin/ps", "/usr/bin/sw_vers"]:
            stub = self.root / Path(command).name
            stub.write_text(f"#!{sys.executable}\n" + STUB)
            stub.chmod(0o755)
            self.replacements[command] = shlex.quote(str(stub))

    def run_script(self, preflight=False, through_homebrew=False):
        script = (self.preflight if preflight else self.uninstall["script"])["args"][1]
        for original, replacement in self.replacements.items():
            script = script.replace(original, replacement)
        self.state_path.write_text(json.dumps(self.state))
        command = ["/bin/sh", "-c", script]
        if through_homebrew:
            script_path = self.root / "uninstall.sh"
            script_path.write_text("export FIXTURE_STATE=" + shlex.quote(str(self.state_path)) + "\n" + script)
            driver = self.root / "driver.rb"
            driver.write_text('''
require "cask/cask_loader"
cask = Cask::CaskLoader.load(CASK_NAME)
original = cask.artifacts.find { |a| a.is_a?(Cask::Artifact::Uninstall) }
script = original.directives.fetch(:script).dup
script[:args] = ["-c", File.read(SCRIPT_PATH)]
# Run the actual Homebrew uninstall-script dispatcher. Omit quit/login_item
# deliberately: those would act on the user's running app, outside this fixture.
Cask::Artifact::Uninstall.new(cask, script: script).uninstall_phase(command: SystemCommand)
'''.replace('CASK_NAME', json.dumps(os.environ['SENTIENT_TEST_CASK']))
                .replace('SCRIPT_PATH', json.dumps(str(script_path))))
            command = ["brew", "ruby", str(driver)]
        result = subprocess.run(command, capture_output=True, text=True,
                                env={**os.environ, "FIXTURE_STATE": str(self.state_path),
                                     "FIXTURE_SCRIPT": str(self.root / "uninstall.sh"),
                                     "HOMEBREW_NO_AUTO_UPDATE": "1"}, timeout=20)
        self.state = json.loads(self.state_path.read_text())
        return result

    def privileged_calls(self):
        return [call for call in self.state["calls"] if call[0] == "sudo"]

    def test_no_helper_never_requests_sudo(self):
        self.assertEqual(self.run_script().returncode, 0)
        self.assertEqual(self.privileged_calls(), [])

    def test_managed_service_without_standalone_plist(self):
        self.state["services"] = [MANAGED]
        self.assertEqual(self.run_script().returncode, 0)
        self.assertEqual(self.state["services"], [])
        actions = [c[0:2] for c in self.state["calls"] if c[0] in ("pmset", "launchctl")]
        self.assertLess(actions.index(["pmset", "-a"]), actions.index(["launchctl", "bootout"]))
        self.assertFalse(any(c[0] == "rm" for c in self.state["calls"]))

    def test_both_helpers_and_legacy_plist(self):
        self.state["services"] = [MANAGED, LEGACY]
        self.plist.write_text("legacy")
        neighbor = self.root / "unrelated.plist"
        neighbor.write_text("preserve")
        self.assertEqual(self.run_script().returncode, 0)
        self.assertEqual(self.state["services"], [])
        self.assertFalse(self.plist.exists())
        self.assertEqual(neighbor.read_text(), "preserve")

    def test_orphan_legacy_plist(self):
        self.plist.write_text("legacy")
        self.assertEqual(self.run_script().returncode, 0)
        self.assertFalse(self.plist.exists())
        self.assertEqual(len(self.privileged_calls()), 1)

    def test_dangling_legacy_symlink(self):
        self.plist.symlink_to(self.root / "missing")
        self.assertEqual(self.run_script().returncode, 0)
        self.assertFalse(self.plist.is_symlink())

    def test_probe_errors_are_not_absence(self):
        self.state["probe_error"] = True
        self.plist.write_text("legacy")
        self.assertNotEqual(self.run_script().returncode, 0)
        self.assertTrue(self.plist.exists())
        self.assertEqual(self.privileged_calls(), [])

    def test_cleanup_failures_keep_plist_and_fail_uninstall(self):
        for mode in ["sudo_fail", "restore_fail", "bootout_noop", "post_probe_error", "delete_fail"]:
            with self.subTest(mode=mode):
                self.state = {"calls": [], "services": [LEGACY], "plist": str(self.plist), mode: True}
                self.plist.write_text("legacy")
                self.assertNotEqual(self.run_script().returncode, 0)
                self.assertTrue(self.plist.exists())
                if mode in ("sudo_fail", "restore_fail"):
                    self.assertEqual(self.state["services"], [LEGACY])
                    self.assertFalse(any(c[:2] == ["launchctl", "bootout"] for c in self.state["calls"]))

    def test_service_disappearing_during_bootout_is_safe(self):
        self.state.update(services=[MANAGED], bootout_race=True)
        self.assertEqual(self.run_script().returncode, 0)
        self.assertEqual(self.state["services"], [])

    def test_running_app_or_failed_process_check_aborts(self):
        for status in [0, 2]:
            with self.subTest(status=status):
                self.state.update(calls=[], services=[MANAGED], pgrep_status=status)
                self.assertNotEqual(self.run_script().returncode, 0)
                self.assertEqual(self.privileged_calls(), [])
                self.assertEqual(self.state["services"], [MANAGED])

    def test_other_user_gui_blocks_system_helper_removal(self):
        self.state.update(services=[MANAGED], pgrep_status=0, process_uid=502)
        self.assertNotEqual(self.run_script().returncode, 0)
        self.assertEqual(self.privileged_calls(), [])

    def test_root_helper_does_not_block_uninstall(self):
        self.state.update(services=[MANAGED], pgrep_status=0, process_uid=0)
        self.assertEqual(self.run_script().returncode, 0)
        self.assertEqual(self.state["services"], [])

    def test_process_disappearance_and_query_failure(self):
        for status, accepted in [(1, True), (2, False)]:
            with self.subTest(status=status):
                self.state.update(calls=[], services=[], pgrep_status=0, ps_status=status)
                self.assertEqual(self.run_script().returncode == 0, accepted)
                self.assertEqual(self.privileged_calls(), [])

    def test_minimum_macos_boundary(self):
        for version, accepted in [("14.7.1", False), ("15.0", False), ("15.3.9", False),
                                  ("15.4", True), ("15.4.1", True), ("15.10", True), ("26.0", True)]:
            with self.subTest(version=version):
                self.state["version"] = version
                self.assertEqual(self.run_script(preflight=True).returncode == 0, accepted)

    def test_homebrew_preserves_failure_and_no_unconditional_sudo(self):
        self.assertTrue(self.uninstall["script"]["must_succeed"])
        self.assertFalse(self.uninstall["script"]["sudo"])
        self.assertNotIn("launchctl", self.uninstall)
        self.assertNotIn("delete", self.uninstall)
        self.assertNotIn("verified", self.cask["url_specs"])

    def test_homebrew_dispatcher_without_helper(self):
        result = self.run_script(through_homebrew=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.privileged_calls(), [])

    def test_homebrew_dispatcher_propagates_cleanup_failure(self):
        self.state.update(services=[MANAGED], restore_fail=True)
        result = self.run_script(through_homebrew=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Error", result.stderr)
        self.assertTrue(any(c[0] == "pmset" for c in self.state["calls"]))
        self.assertEqual(self.state["services"], [MANAGED])

    def test_zap_preserves_knowledge_base(self):
        paths = next(a["zap"][0]["trash"] for a in self.cask["artifacts"] if "zap" in a)
        self.assertIn("~/Library/Application Support/SentientOS", paths)
        self.assertFalse(any("Knowledge Base" in p for p in paths))


if __name__ == "__main__":
    unittest.main(verbosity=2)
