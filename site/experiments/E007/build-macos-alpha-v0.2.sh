#!/usr/bin/env bash
set -euo pipefail

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
BUILD_DIR="$(mktemp -d "$DOWNLOADS_DIR/pocket-i-alpha-build.XXXXXX")"
REPO_DIR="$BUILD_DIR/joinmultiplayer.ai"

echo "Building Pocket i in: $BUILD_DIR"
git clone --depth 1 --branch agent/game-loop-v0.1 \
  https://github.com/yukakust/joinmultiplayer.ai.git "$REPO_DIR"

python3 -m venv "$BUILD_DIR/venv"
"$BUILD_DIR/venv/bin/python" -m pip install --disable-pip-version-check \
  pyinstaller==6.16.0

cd "$REPO_DIR/desktop/app"
npm ci
CSC_IDENTITY_AUTO_DISCOVERY=false \
POCKET_I_BUILD_PYTHON="$BUILD_DIR/venv/bin/python" \
  ./build-current-platform.sh

DMG_PATH="$(find "$REPO_DIR/desktop/app/dist" -maxdepth 1 -type f -name '*.dmg' -print -quit)"
if [ -z "$DMG_PATH" ]; then
  echo "The build finished without a DMG." >&2
  exit 1
fi

APP_VERSION="$(node -p "require('$REPO_DIR/desktop/app/package.json').version")"
OUTPUT_PATH="$DOWNLOADS_DIR/Pocket-i-$APP_VERSION-$(uname -m).dmg"
if [ -e "$OUTPUT_PATH" ]; then
  echo "Refusing to overwrite: $OUTPUT_PATH" >&2
  exit 1
fi
cp "$DMG_PATH" "$OUTPUT_PATH"
shasum -a 256 "$OUTPUT_PATH"
echo "DMG_READY: $OUTPUT_PATH"
open -R "$OUTPUT_PATH"

