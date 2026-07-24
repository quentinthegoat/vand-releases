# VAND

**Your AI doesn't have a parent company.**

VAND is a local-first personal AI for Windows. It runs on your computer, learns
from your own life, and keeps its data in one encrypted file on your disk.

[Download the 14-day trial](https://vand.space/download) ·
[Own VAND for €79 once](https://vand.space/founders) ·
[How your data stays yours](https://vand.space/security)

[![VAND dashboard showing local demo data](https://vand.space/demo/screenshot-main.png)](https://vand.space/download)

## What makes it different

- Local AI: your prompts and personal history are processed on your machine.
- Real memory: VAND can recall your journal, habits, health, goals, and prior
  context without uploading your life to a company server.
- Offline ownership: paid keys are verified locally and keep working even if
  VAND's website disappears.
- No account and no subscription: try the complete app for 14 days, then buy it
  once if it earns a permanent place on your computer.

## Download

The latest Windows x64 installer is on the
[Releases page](https://github.com/quentinthegoat/vand-releases/releases/latest).

VAND is currently unsigned; the first sales will fund code signing. Windows may
show a SmartScreen warning, so the
[download guide](https://vand.space/download) explains the exact installation
steps and every release publishes its SHA-256 checksum.

For `VAND-0.13.1-x64.exe`, the expected SHA-256 is:

```text
73151516A9FE307E833FBA557E60D52168A00D2928DEDF5B5DB28203211CDB8E
```

Verify it in PowerShell before opening the installer:

```powershell
Get-FileHash .\VAND-0.13.1-x64.exe -Algorithm SHA256
```

## About this repository

This public repository hosts official VAND installers and update metadata. The
application source remains private. Product details, pricing, privacy, and
support live at [vand.space](https://vand.space).
