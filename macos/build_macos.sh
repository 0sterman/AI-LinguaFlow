#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

APP_NAME="LinguaFlow AI"
BUNDLE_ID="com.oster.linguaflow"
VERSION="$(python3 - <<'PY'
from translator_app import __version__
print(__version__)
PY
)"
export MACOSX_DEPLOYMENT_TARGET="${MACOSX_DEPLOYMENT_TARGET:-11.0}"

python3 -m pip install -r requirements-macos.txt

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

python3 -m PyInstaller \
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
hdiutil create \
  -volname "$APP_NAME $VERSION" \
  -srcfolder "$DMG_DIR" \
  -ov \
  -format UDZO \
  "$ROOT_DIR/dist/$APP_NAME-$VERSION-macOS-x86_64.dmg"

echo "Built: $ROOT_DIR/dist/$APP_NAME-$VERSION-macOS-x86_64.dmg"
