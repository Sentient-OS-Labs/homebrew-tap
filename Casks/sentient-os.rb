cask "sentient-os" do
  version "1.2"
  # ── ⚠️ FILL AT RELEASE ────────────────────────────────────────────────────────
  # The DMG doesn't exist until `Scripts/release.sh` runs and uploads it to the
  # GitHub Release. After that, compute the real checksum and paste it here:
  #     shasum -a 256 SentientOS-1.0.dmg
  # This placeholder is intentionally NOT a valid hash so a stale/unfinished cask
  # can never install. `brew audit` will (correctly) fail until it's replaced.
  sha256 "d6d582c7397f06651311a2a4dbbe8c425c1886649dc9248dd3edc79c482c9910"

  # release.sh tags releases with the bare version (NO "v" prefix) and names the
  # asset SentientOS-<version>.dmg — keep this URL in lockstep with that script.
  url "https://github.com/Sentient-OS-Labs/sentient-os/releases/download/#{version}/SentientOS-#{version}.dmg",
      verified: "github.com/Sentient-OS-Labs/sentient-os/"
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
  # Hard macOS 15.0 (Sequoia) floor — enforced before any download.
  depends_on macos: :sequoia

  app "Sentient OS.app"

  # Sentient installs a ROOT wake-helper LaunchDaemon (runs the app's own binary
  # with --wake-helper; there is NO separate helper binary) and enables a login
  # item. Unload the daemon, quit the app, drop the login item, remove the plist.
  uninstall launchctl:  "jesai.Sentient-OS-macOS.WakeHelper",
            quit:       "jesai.Sentient-OS-macOS",
            login_item: "Sentient OS",
            delete:     "/Library/LaunchDaemons/jesai.Sentient-OS-macOS.WakeHelper.plist"

  # `brew uninstall --zap` scrub. Confirm/expand with `brew generate-zap` against a
  # real installed build before shipping.
  # NOTE: the user's Knowledge Base (~/Sentient OS - Knowledge Base) is their own
  # canonical data and is deliberately NOT zapped — like Obsidian never deletes a
  # user's vault.
  zap trash: [
    "~/Library/Application Support/jesai.Sentient-OS-macOS",
    "~/Library/Caches/jesai.Sentient-OS-macOS",
    "~/Library/Caches/SentryCrash/Sentient OS",
    "~/Library/HTTPStorages/jesai.Sentient-OS-macOS",
    "~/Library/Preferences/jesai.Sentient-OS-macOS.plist",
    "~/Library/Saved Application State/jesai.Sentient-OS-macOS.savedState",
  ]
end
