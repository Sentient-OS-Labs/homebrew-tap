cask "sentient-os" do
  version "2.8"
  sha256 "0e23e4724792c0e4dfc8fbce6bf84f1c3d674001642845212133672ba9e33192"

  # A second version component identifies a build-only release.
  url "https://github.com/Sentient-OS-Labs/sentient-os/releases/download/#{version.csv.first}#{"-build#{version.csv.second}" if version.csv.second}/SentientOS-#{version.csv.first}.dmg"
  name "Sentient OS"
  desc "On-device AI that reads your life and proactively acts on it"
  homepage "https://sentient-os.ai/"

  # The app self-updates via Sparkle; this is Sparkle's own appcast (the app's
  # SUFeedURL). Homebrew reads it only to know the latest version for autobump.
  livecheck do
    url "https://sentient-os.ai/appcast.xml"
    strategy :sparkle, &:short_version
  end

  # Sparkle owns updates in-app, so `brew upgrade` defers to it (no double-update).
  auto_updates true
  # Require Apple silicon and macOS Sequoia or later.
  depends_on arch: :arm64
  depends_on macos: :sequoia

  app "Sentient OS.app"

  # Keep the 15.4 minimum without a deprecated arbitrary-Ruby flight block.
  preflight_steps do
    run "/bin/sh", args: ["-c", <<~SH]
      set -eu
      version=$(/usr/bin/sw_vers -productVersion)
      major=${version%%.*}
      rest=${version#*.}
      minor=${rest%%.*}
      if [ "$major" -lt 15 ] || { [ "$major" -eq 15 ] && [ "$minor" -lt 4 ]; }; then
        echo "Sentient OS requires macOS 15.4 or later." >&2
        exit 1
      fi
    SH
  end

  # Probe without sudo: SMAppService keeps the managed plist inside the app,
  # while older installs used a standalone plist. Homebrew's launchctl/delete
  # directives request sudo even when there is nothing to remove.
  uninstall quit:       "jesai.Sentient-OS-macOS",
            login_item: "Sentient OS",
            script:     {
              executable:   "/bin/sh",
              args:         ["-c", <<~SH],
                set -eu

                # Homebrew's quit directive only warns on timeout. Do not kill
                # the helper's safety timers while the app can still use it.
                if pids=$(/usr/bin/pgrep -x "Sentient OS"); then
                  for pid in $pids; do
                    if uid=$(/bin/ps -p "$pid" -o uid=); then
                      # Root processes are the helper. Any user's GUI can
                      # control this system-wide service, not just our user.
                      if [ "$uid" -ne 0 ]; then
                        echo "Quit Sentient OS in all user sessions before uninstalling." >&2
                        exit 1
                      fi
                    else
                      status=$?
                      # A process can exit between pgrep and ps.
                      [ "$status" -eq 1 ] || exit "$status"
                    fi
                  done
                else
                  status=$?
                  [ "$status" -eq 1 ] || exit "$status"
                fi

                for label in jesai.Sentient-OS-macOS.WakeHelper.Managed jesai.Sentient-OS-macOS.WakeHelper; do
                  target="system/$label"
                  if /bin/launchctl print "$target" >/dev/null 2>&1; then
                    # The helper can set disablesleep=1. Restore sleep BEFORE
                    # stopping it, so a failed restore leaves its timers alive.
                    /usr/bin/sudo /usr/bin/pmset -a disablesleep 0
                    /usr/bin/sudo /bin/launchctl bootout "$target" || true
                    if /bin/launchctl print "$target" >/dev/null 2>&1; then
                      echo "Could not remove $target; uninstall stopped." >&2
                      exit 1
                    else
                      status=$?
                      [ "$status" -eq 113 ] || exit "$status"
                    fi
                  else
                    status=$?
                    [ "$status" -eq 113 ] || exit "$status"
                  fi
                done

                # Only legacy releases installed this file. The managed plist
                # goes away with the app bundle. Never delete a shared directory.
                plist=/Library/LaunchDaemons/jesai.Sentient-OS-macOS.WakeHelper.plist
                if [ -e "$plist" ] || [ -L "$plist" ]; then
                  /usr/bin/sudo /bin/rm -f -- "$plist"
                fi
              SH
              must_succeed: true,
              sudo:         false,
            }

  # User-data paths owned by AppSupport, CrashReporting, and Uninstall in the app.
  # NOTE: the user's Knowledge Base (~/Sentient OS - Knowledge Base) is their own
  # canonical data and is deliberately NOT zapped — like Obsidian never deletes a
  # user's vault.
  zap trash: [
    "~/Library/Application Support/jesai.Sentient-OS-macOS",
    "~/Library/Application Support/SentientOS",
    "~/Library/Caches/jesai.Sentient-OS-macOS",
    "~/Library/Caches/SentientOS",
    "~/Library/HTTPStorages/jesai.Sentient-OS-macOS",
    "~/Library/Logs/SentientOS",
    "~/Library/Preferences/jesai.Sentient-OS-macOS.plist",
    "~/Library/Saved Application State/jesai.Sentient-OS-macOS.savedState",
    "~/Library/WebKit/jesai.Sentient-OS-macOS",
  ]
end
