# VAND

**Track everything, everytime.**

VAND is a desktop app for **Windows and Mac** that tracks anything you can
name. Type it in plain words — *slept 7h, ran 5k, spent 12 on lunch* — and it
files each one. Everything stays in one encrypted file on your own computer.
No account, no cloud.

[Download the 14-day trial](https://vand.space/download) ·
[Pricing](https://vand.space/pricing) ·
[How your data stays yours](https://vand.space/security)

## What it does

- **You define the trackers.** Sleep, mood, money, guitar practice — anything.
  A tracker that does not exist yet is offered the moment you type it.
- **One line, several logs.** *slept 5h, 3 coffees, anxious* becomes three
  entries, and shows you how it read each one before saving.
- **Your own data in.** Apple Health, bank statements (CSV/OFX), and Calendar
  on Mac — all read on your computer.
- **Answers from your records.** *How much did I sleep last week* is read out
  of your vault, not guessed by a model.
- **AI is optional.** Paste your own Anthropic or OpenAI key and prompts go
  straight from your computer to that provider — VAND runs no server in
  between. Or use a local Ollama model. Tracking needs neither.
- **Bought once.** No subscription. The licence key is verified offline and
  keeps working even if this website disappears.

## Download

Get the installer from **[vand.space/download](https://vand.space/download)**
or the [latest release](https://github.com/quentinthegoat/vand-releases/releases/latest).

| | File |
|---|---|
| Windows 10/11 (x64) | `VAND-0.14.1-x64.exe` |
| Mac, Apple Silicon | `VAND-0.14.1-arm64.dmg` |
| Mac, Intel | `VAND-0.14.1-x64.dmg` |

VAND is **unsigned** — a code-signing certificate costs money this project has
not made yet. So the first launch needs one extra click:

- **Windows:** SmartScreen → **More info** → **Run anyway**.
- **Mac:** System Settings → Privacy & Security → **Open Anyway**.

Every release lists its SHA-256 checksums so you can verify the file you got.

```text
9787ef6143611b0c54048850509879f59d7e9576952c383a9ecde8dfebcfeb78  VAND-0.14.1-x64.exe
1cf3f8754f8c6075836f925d47a0d16dac8f77fb91b7a39b4a10b85282cf0372  VAND-0.14.1-arm64.dmg
7f92dacb49e7bac50bc7630b334a43af75d198cb7a2aebb4c2fd475a090416e3  VAND-0.14.1-x64.dmg
```

## About this repository

This is the **official download host for VAND**, run by the same person who
runs [vand.space](https://vand.space): Quentin Vandorme, the developer. The
website's download buttons link to the release files in this repository, and
the app checks this repository for updates. The application source is private.

Support: vand.app.ai@gmail.com
