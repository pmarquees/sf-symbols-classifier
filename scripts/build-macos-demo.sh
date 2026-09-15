#!/bin/sh
set -eu

APP_NAME="SFSymbolFinderDemo"
BUNDLE_ID="io.pedromarques.sfsymbolfinderdemo"
ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
DIST_DIR="$ROOT_DIR/dist"
APP_BUNDLE="$DIST_DIR/$APP_NAME.app"
DEMO_PACKAGE_DIR="$ROOT_DIR/Examples/macOS/SFSymbolFinderDemo"
SCRATCH_DIR="$ROOT_DIR/.build/demo"
MODE="${1:-run}"

cd "$ROOT_DIR"

/usr/bin/pkill -x "$APP_NAME" 2>/dev/null || true
/usr/bin/xcrun swift build \
    --package-path "$DEMO_PACKAGE_DIR" \
    --scratch-path "$SCRATCH_DIR" \
    --product "$APP_NAME"
BIN_DIR=$(/usr/bin/xcrun swift build \
    --package-path "$DEMO_PACKAGE_DIR" \
    --scratch-path "$SCRATCH_DIR" \
    --show-bin-path)

/bin/rm -rf "$APP_BUNDLE"
/bin/mkdir -p "$APP_BUNDLE/Contents/MacOS" "$APP_BUNDLE/Contents/Resources"
/bin/cp "$BIN_DIR/$APP_NAME" "$APP_BUNDLE/Contents/MacOS/$APP_NAME"

for RESOURCE_BUNDLE in "$BIN_DIR"/*.bundle; do
    if [ -d "$RESOURCE_BUNDLE" ]; then
        /bin/cp -R "$RESOURCE_BUNDLE" "$APP_BUNDLE/Contents/Resources/"
    fi
done

/usr/bin/plutil -create xml1 "$APP_BUNDLE/Contents/Info.plist"
/usr/libexec/PlistBuddy -c "Add :CFBundlePackageType string APPL" "$APP_BUNDLE/Contents/Info.plist"
/usr/libexec/PlistBuddy -c "Add :CFBundleExecutable string $APP_NAME" "$APP_BUNDLE/Contents/Info.plist"
/usr/libexec/PlistBuddy -c "Add :CFBundleIdentifier string $BUNDLE_ID" "$APP_BUNDLE/Contents/Info.plist"
/usr/libexec/PlistBuddy -c "Add :CFBundleName string $APP_NAME" "$APP_BUNDLE/Contents/Info.plist"
/usr/libexec/PlistBuddy -c "Add :LSMinimumSystemVersion string 14.0" "$APP_BUNDLE/Contents/Info.plist"
/usr/libexec/PlistBuddy -c "Add :NSPrincipalClass string NSApplication" "$APP_BUNDLE/Contents/Info.plist"
/usr/libexec/PlistBuddy -c "Add :NSHighResolutionCapable bool true" "$APP_BUNDLE/Contents/Info.plist"

case "$MODE" in
    --debug)
        exec /usr/bin/lldb "$APP_BUNDLE/Contents/MacOS/$APP_NAME"
        ;;
    --logs)
        /usr/bin/open -n "$APP_BUNDLE"
        exec /usr/bin/log stream --info --predicate "process == '$APP_NAME'"
        ;;
    --telemetry)
        /usr/bin/open -n "$APP_BUNDLE"
        exec /usr/bin/log stream --info --predicate "subsystem == '$BUNDLE_ID'"
        ;;
    --verify)
        /usr/bin/open -n "$APP_BUNDLE"
        /bin/sleep 1
        /usr/bin/pgrep -x "$APP_NAME" >/dev/null
        echo "$APP_NAME built, launched, and verified."
        ;;
    run|"")
        /usr/bin/open -n "$APP_BUNDLE"
        ;;
    *)
        echo "Usage: sh scripts/build-macos-demo.sh [--debug|--logs|--telemetry|--verify]" >&2
        exit 64
        ;;
esac
