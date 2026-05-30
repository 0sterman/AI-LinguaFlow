# LinguaFlow AI for macOS

This is the macOS packaging path for LinguaFlow AI.

Important limits:

- Build and final verification must be done on macOS with Xcode Command Line Tools installed.
- The package targets Intel Macs (`x86_64`) and sets `MACOSX_DEPLOYMENT_TARGET=12.0` by default to match the supported macOS range of the bundled Qt/PySide runtime.
- The build was created and tested on macOS Ventura. Expected supported Intel macOS versions are macOS 12 Monterey and newer, but older or patched systems still need real-device testing.
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

If `Cmd+C+C` does not work, grant Accessibility permission and restart LinguaFlow AI.
