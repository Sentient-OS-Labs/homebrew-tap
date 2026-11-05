# Sentient OS — Homebrew Tap

The official [Homebrew](https://brew.sh) tap for **[Sentient OS](https://sentient-os.ai)** — an AI that
knows your entire life, privately, on your own Mac, and proactively does things for you.

## Install

```sh
brew install --cask sentient-os-labs/tap/sentient-os
```

That single, fully-qualified command taps this repo and installs the app in one step. Use it exactly
as written: since Homebrew 6.0.0, third-party taps require explicit trust, but the fully-qualified
`user/tap/cask` form trusts just this one cask and skips the prompt. (Avoid the two-step
`brew tap …` + `brew install sentient-os` form — it triggers a trust warning.)

**Requirements:** Apple silicon and macOS 15.4 or newer.

## Update

Sentient OS keeps itself current automatically (via its built-in updater). Homebrew won't fight that.
If you ever want Homebrew to reconcile its record with the latest release:

```sh
brew update && brew upgrade --cask sentient-os
```

## Uninstall

```sh
brew uninstall --cask sentient-os          # remove the app + its background helper
brew uninstall --zap --cask sentient-os    # also remove local app data, models, caches and preferences
```

Your Knowledge Base at `~/Sentient OS - Knowledge Base` is **your** data and is never touched by
uninstall or zap — delete it yourself if you want it gone.

Quit Sentient in all user sessions before uninstalling. The cask checks both the current managed wake helper and the
legacy helper without administrator access. It requests your password only when a registered
helper or legacy plist needs removal. Cleanup restores normal sleep before stopping a helper,
verifies that the service is gone, and stops the uninstall if cleanup fails.

The current helper is registered through `SMAppService`, with its plist **inside the app bundle**.
An empty `/Library/LaunchDaemons` does not prove that the helper is absent. It still runs as root
because the current overnight scheduler changes system-wide `pmset` sleep/wake settings; a
per-user LaunchAgent cannot replace those privileged operations. The cask stops the registered
launchd job; it does not reset macOS's shared background-item database or other apps' wake events.

### Existing installs and manual cleanup

Homebrew keeps the uninstall instructions recorded at installation time. `brew update` alone
does not replace an old installed receipt, so existing installs can still use the broken cleanup
and request a password unnecessarily. If an earlier uninstall already removed the app, inspect
both service names:

```sh
launchctl print system/jesai.Sentient-OS-macOS.WakeHelper.Managed
launchctl print system/jesai.Sentient-OS-macOS.WakeHelper
```

For a service that is present, after quitting Sentient in all user sessions, restore sleep and stop that exact service
(substitute the legacy label if that is the one found):

```sh
sudo pmset -a disablesleep 0 && sudo launchctl bootout system/jesai.Sentient-OS-macOS.WakeHelper.Managed
launchctl print system/jesai.Sentient-OS-macOS.WakeHelper.Managed
```

The final check should report that the service cannot be found. Once the **legacy** service is
also absent, remove its standalone plist only if it exists:

```sh
plist=/Library/LaunchDaemons/jesai.Sentient-OS-macOS.WakeHelper.plist
if [ -e "$plist" ] || [ -L "$plist" ]; then
  sudo rm -f -- "$plist"
fi
```

Do not remove a service's plist if stopping that service failed. For full app-managed cleanup,
including native service unregistration and pending scheduled wakes, use the app's uninstall
flow while the app is still installed. That flow also deletes app data and the Knowledge Base;
back up anything you want to keep first.

## Testing changes

Point a local Homebrew tap at the checkout being tested and trust that cask, then run:

```sh
brew style Casks/sentient-os.rb
brew audit --cask YOUR-OWNER/YOUR-TAP/sentient-os
SENTIENT_TEST_CASK=YOUR-OWNER/YOUR-TAP/sentient-os python3 tests/test_cask.py
```

The regression suite loads Homebrew's serialized cask and executes its shell scripts with isolated
command fixtures. It covers the macOS version boundary, absent and registered helpers, legacy
plists, failed cleanup, and Knowledge Base preservation. It never changes live services, power
settings, or user data. A real registered-helper uninstall still needs a disposable Mac or VM.

## What this repo is

Just a git repository of one [Homebrew Cask](https://docs.brew.sh/Cask-Cookbook) definition
(`Casks/sentient-os.rb`). The app itself, its source, and its releases live at
[`Sentient-OS-Labs/sentient-os`](https://github.com/Sentient-OS-Labs/sentient-os). The notarized DMG
each cask version points at is published as a GitHub Release asset there.

---

*Private by design. Your files never leave this Mac.*
