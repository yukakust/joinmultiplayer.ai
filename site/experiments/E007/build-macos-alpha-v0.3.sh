#!/usr/bin/env bash
set -euo pipefail

EXPECTED_REVISION="c36e807"

if [ "$(uname -s)" != "Darwin" ]; then
  echo "This builder must run on macOS." >&2
  exit 1
fi

for command_name in git python3 npm node; do
  if ! command -v "$command_name" >/dev/null 2>&1; then
    echo "$command_name is required but was not found." >&2
    exit 1
  fi
done

DOWNLOADS_DIR="$HOME/Downloads"
mkdir -p "$DOWNLOADS_DIR"
BUILD_DIR="$(mktemp -d "$DOWNLOADS_DIR/pocket-i-alpha8-build.XXXXXX")"
REPO_DIR="$BUILD_DIR/joinmultiplayer.ai"

echo "Building Pocket i from: $EXPECTED_REVISION"
git init -q "$REPO_DIR"
git -C "$REPO_DIR" remote add origin https://github.com/yukakust/joinmultiplayer.ai.git
git -C "$REPO_DIR" fetch -q --depth 1 origin "$EXPECTED_REVISION"
git -C "$REPO_DIR" checkout -q --detach FETCH_HEAD
ACTUAL_REVISION="$(git -C "$REPO_DIR" rev-parse --short=7 HEAD)"
if [ "$ACTUAL_REVISION" != "$EXPECTED_REVISION" ]; then
  echo "Wrong source revision: $ACTUAL_REVISION" >&2
  exit 1
fi

python3 -m venv "$BUILD_DIR/venv"
"$BUILD_DIR/venv/bin/python" -m pip install --disable-pip-version-check pyinstaller==6.16.0

cd "$REPO_DIR"
PYTHONPATH=desktop "$BUILD_DIR/venv/bin/python" -m unittest discover -s desktop/tests -v
cd "$REPO_DIR/desktop/app"
npm ci
npm test
CSC_IDENTITY_AUTO_DISCOVERY=false \
POCKET_I_BUILD_PYTHON="$BUILD_DIR/venv/bin/python" \
  ./build-current-platform.sh

DMG_PATH="$(find "$REPO_DIR/desktop/app/dist" -maxdepth 1 -type f -name '*.dmg' -print -quit)"
if [ -z "$DMG_PATH" ]; then
  echo "The build finished without a DMG." >&2
  exit 1
fi

APP_VERSION="$(node -p "require('$REPO_DIR/desktop/app/package.json').version")"
OUTPUT_PATH="$DOWNLOADS_DIR/Pocket-i-$APP_VERSION-$(uname -m)-$EXPECTED_REVISION.dmg"
if [ -e "$OUTPUT_PATH" ]; then
  echo "Refusing to overwrite: $OUTPUT_PATH" >&2
  exit 1
fi
cp "$DMG_PATH" "$OUTPUT_PATH"
shasum -a 256 "$OUTPUT_PATH"
echo "DMG_READY: $OUTPUT_PATH"
rm -rf "$BUILD_DIR"
echo "TEMP_BUILD_REMOVED: $BUILD_DIR"
open -R "$OUTPUT_PATH"
