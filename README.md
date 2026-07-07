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

**Requirements:** macOS 15 (Sequoia) or newer.

## Update

Sentient OS keeps itself current automatically (via its built-in updater). Homebrew won't fight that.
If you ever want Homebrew to reconcile its record with the latest release:

```sh
brew update && brew upgrade --cask sentient-os
```

## Uninstall

```sh
brew uninstall --cask sentient-os          # remove the app + its background helper
brew uninstall --zap --cask sentient-os    # also scrub caches/preferences
```

Your Knowledge Base at `~/Sentient OS - Knowledge Base` is **your** data and is never touched by
uninstall or zap — delete it yourself if you want it gone.

## What this repo is

Just a git repository of one [Homebrew Cask](https://docs.brew.sh/Cask-Cookbook) definition
(`Casks/sentient-os.rb`). The app itself, its source, and its releases live at
[`Sentient-OS-Labs/sentient-os`](https://github.com/Sentient-OS-Labs/sentient-os). The notarized DMG
each cask version points at is published as a GitHub Release asset there.

---

*Private by design. Your files never leave this Mac.*
