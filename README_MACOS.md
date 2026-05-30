# LinguaFlow AI for macOS

This is the macOS packaging path for LinguaFlow AI.

## Download

The current macOS test build is attached to the GitHub `v1.0.9` release:

```text
LinguaFlow-AI-v1.0.9-macOS-x86_64.dmg
```

Open the DMG, drag `LinguaFlow AI.app` to `Applications`, then launch it from `Applications`.

## Supported macOS Versions

- Architecture: Intel x86_64.
- Expected support: macOS 12 Monterey or newer.
- Built and tested by the project owner: macOS 13 Ventura.
- Expected, but not fully verified on every device: macOS 14 Sonoma and macOS 15 Sequoia.
- Apple Silicon: not officially tested; the Intel build may run through Rosetta 2.

Important limits:

- Build and final verification must be done on macOS with Xcode Command Line Tools installed.
- The package targets Intel Macs (`x86_64`) and sets `MACOSX_DEPLOYMENT_TARGET=12.0` by default to match the supported macOS range of the bundled Qt/PySide runtime.
- Older or patched systems still need real-device testing.
- A signed/notarized public build requires an Apple Developer ID certificate and notarization credentials. Without them, macOS Gatekeeper can show warnings.
- `Cmd+C+C` global capture requires Accessibility permission: System Settings -> Privacy & Security -> Accessibility -> LinguaFlow AI.

Build on a Mac:

```bash
python3 -m venv .venv
source .venv/bin/activate
./macos/build_macos.sh
```

The resulting installer image is created in `dist/`:

```text
dist/LinguaFlow AI-<version>-macOS-x86_64.dmg
```

Runtime shortcuts on macOS:

- `Cmd (Ctrl)+C+C` - fast selected-text translation.
- `Cmd (Ctrl)+Enter` - translate in the main window.
- `Esc` - clear the source text.

If `Cmd+C+C` does not work, grant Accessibility and Input Monitoring permission, then restart LinguaFlow AI.
