cask "sentient-os" do
  version "2.7.5,22"
  sha256 "4fb0eab543c30cdcce85960d5ab86c4834f17004fafa6c0b1a09e43f1af38460"

  # A second version component identifies a build-only release.
  url "https://github.com/Sentient-OS-Labs/sentient-os/releases/download/#{version.csv.first}#{version.csv.second ? "-build#{version.csv.second}" : ""}/SentientOS-#{version.csv.first}.dmg",
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
  # Require Apple silicon and macOS Sequoia or later.
  depends_on arch: :arm64
  depends_on macos: :sequoia

  app "Sentient OS.app"

  # Homebrew’s macOS dependency names cover major releases; enforce the minor version here.
  preflight do
    odie "Sentient OS #{version} requires macOS 15.4 or later." if MacOS.full_version < "15.4"
  end

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
