#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

APP_NAME="LinguaFlow AI"
BUNDLE_ID="com.oster.linguaflow"
PYTHON_BIN="${PYTHON:-python3}"
VERSION="$("$PYTHON_BIN" - <<'PY'
from translator_app import __version__
print(__version__)
PY
)"
export MACOSX_DEPLOYMENT_TARGET="${MACOSX_DEPLOYMENT_TARGET:-12.0}"

"$PYTHON_BIN" -m pip install --no-compile -r requirements-macos.txt

ICONSET_DIR="build/macos/app_icon.iconset"
mkdir -p "$ICONSET_DIR"
sips -z 16 16 assets/app_icon.png --out "$ICONSET_DIR/icon_16x16.png" >/dev/null
sips -z 32 32 assets/app_icon.png --out "$ICONSET_DIR/icon_16x16@2x.png" >/dev/null
sips -z 32 32 assets/app_icon.png --out "$ICONSET_DIR/icon_32x32.png" >/dev/null
sips -z 64 64 assets/app_icon.png --out "$ICONSET_DIR/icon_32x32@2x.png" >/dev/null
sips -z 128 128 assets/app_icon.png --out "$ICONSET_DIR/icon_128x128.png" >/dev/null
sips -z 256 256 assets/app_icon.png --out "$ICONSET_DIR/icon_128x128@2x.png" >/dev/null
sips -z 256 256 assets/app_icon.png --out "$ICONSET_DIR/icon_256x256.png" >/dev/null
sips -z 512 512 assets/app_icon.png --out "$ICONSET_DIR/icon_256x256@2x.png" >/dev/null
sips -z 512 512 assets/app_icon.png --out "$ICONSET_DIR/icon_512x512.png" >/dev/null
sips -z 1024 1024 assets/app_icon.png --out "$ICONSET_DIR/icon_512x512@2x.png" >/dev/null
iconutil -c icns "$ICONSET_DIR" -o "assets/app_icon.icns"

rm -rf build "$ROOT_DIR/dist/$APP_NAME.app" "$ROOT_DIR/dist/$APP_NAME-$VERSION-macOS-x86_64.dmg"

"$PYTHON_BIN" -m PyInstaller \
  --windowed \
  --noconfirm \
  --name "$APP_NAME" \
  --icon assets/app_icon.icns \
  --osx-bundle-identifier "$BUNDLE_ID" \
  --target-architecture x86_64 \
  --add-data "assets/app_icon.png:assets" \
  --add-data "assets/app_icon.icns:assets" \
  --add-data "assets/dropdown_arrow.svg:assets" \
  --hidden-import keyring.backends.macOS \
  translator_app/__main__.py

APP_PATH="$ROOT_DIR/dist/$APP_NAME.app"
set_plist_value() {
  local key="$1"
  local type="$2"
  local value="$3"
  local plist="$4"

  /usr/libexec/PlistBuddy -c "Set :$key $value" "$plist" 2>/dev/null || \
    /usr/libexec/PlistBuddy -c "Add :$key $type $value" "$plist"
}

INFO_PLIST="$APP_PATH/Contents/Info.plist"
set_plist_value "CFBundleShortVersionString" "string" "$VERSION" "$INFO_PLIST"
set_plist_value "CFBundleVersion" "string" "$VERSION" "$INFO_PLIST"
set_plist_value "LSMinimumSystemVersion" "string" "$MACOSX_DEPLOYMENT_TARGET" "$INFO_PLIST"
/usr/libexec/PlistBuddy -c "Add :NSAppleEventsUsageDescription string LinguaFlow AI uses macOS automation only to bring the translator window to the front after Cmd+C+C." "$APP_PATH/Contents/Info.plist" 2>/dev/null || true

if [[ -n "${CODESIGN_IDENTITY:-}" ]]; then
  codesign --force --deep --options runtime --timestamp --sign "$CODESIGN_IDENTITY" "$APP_PATH"
else
  codesign --force --deep --sign - "$APP_PATH"
fi

codesign --verify --deep --strict --verbose=2 "$APP_PATH"

DMG_DIR="build/macos/dmg"
rm -rf "$DMG_DIR"
mkdir -p "$DMG_DIR"
cp -R "$APP_PATH" "$DMG_DIR/"
ln -s /Applications "$DMG_DIR/Applications"
cat > "$DMG_DIR/Open LinguaFlow AI with log.command" <<'SH'
#!/usr/bin/env bash
set +e

LOG="$HOME/Desktop/LinguaFlow-AI-startup.log"
APP_PATH="$(cd "$(dirname "$0")" && pwd)/LinguaFlow AI.app"
EXE_PATH="$APP_PATH/Contents/MacOS/LinguaFlow AI"

{
  echo "LinguaFlow AI macOS startup diagnostics"
  echo "Date: $(date)"
  echo
  echo "macOS:"
  sw_vers
  echo
  echo "Kernel/CPU:"
  uname -a
  echo "Machine: $(uname -m)"
  echo
  echo "App path:"
  echo "$APP_PATH"
  echo
  echo "Bundle files:"
  ls -la "$APP_PATH"
  ls -la "$APP_PATH/Contents"
  ls -la "$APP_PATH/Contents/MacOS"
  echo
  echo "Executable file info:"
  file "$EXE_PATH"
  echo
  echo "Quarantine attributes:"
  xattr -lr "$APP_PATH"
  echo
  echo "Code signature verification:"
  codesign --verify --deep --strict --verbose=4 "$APP_PATH"
  echo "codesign exit code: $?"
  echo
  echo "Gatekeeper assessment:"
  spctl --assess --type execute --verbose=4 "$APP_PATH"
  echo "spctl exit code: $?"
  echo
  echo "Starting executable directly:"
  "$EXE_PATH"
  echo "app exit code: $?"
} >"$LOG" 2>&1

open -R "$LOG"
echo "Diagnostic log saved to:"
echo "$LOG"
echo
echo "Send this log text back to Roman/Codex."
read -r -p "Press Enter to close this window..."
SH
chmod +x "$DMG_DIR/Open LinguaFlow AI with log.command"
hdiutil create \
  -volname "$APP_NAME $VERSION" \
  -srcfolder "$DMG_DIR" \
  -ov \
  -format UDZO \
  "$ROOT_DIR/dist/$APP_NAME-$VERSION-macOS-x86_64.dmg"

echo "Built: $ROOT_DIR/dist/$APP_NAME-$VERSION-macOS-x86_64.dmg"
