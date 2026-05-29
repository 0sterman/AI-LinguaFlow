# LinguaFlow AI for macOS

This is the macOS packaging path for LinguaFlow AI.

Important limits:

- Build and final verification must be done on macOS with Xcode Command Line Tools installed.
- The package targets Intel Macs (`x86_64`) and sets `MACOSX_DEPLOYMENT_TARGET=11.0` by default. That is the realistic target for many 2015 Macs that can run macOS Big Sur or newer.
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

- `Cmd+C+C` - fast selected-text translation.
- `Cmd+Enter` - translate in the main window.
- `Esc` - clear the source text.

If `Cmd+C+C` does not work, grant Accessibility permission and restart LinguaFlow AI.
