#!/usr/bin/env bash
set -euo pipefail

EXPECTED_REVISION="ca5bbde42ec193c0d362bb1e41650ce9a9cf59d7"
SHORT_REVISION="ca5bbde"

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
BUILD_DIR="$(mktemp -d "$DOWNLOADS_DIR/pocket-i-checkpoint7c-build.XXXXXX")"
REPO_DIR="$BUILD_DIR/joinmultiplayer.ai"
cleanup() {
  if [ -d "$BUILD_DIR" ]; then
    rm -rf -- "$BUILD_DIR"
  fi
}
trap cleanup EXIT

echo "Building Pocket i from: $SHORT_REVISION"
git clone -q --depth 50 --branch agent/game-loop-v0.1 \
  https://github.com/yukakust/joinmultiplayer.ai.git "$REPO_DIR"
git -C "$REPO_DIR" checkout -q --detach "$EXPECTED_REVISION"
ACTUAL_REVISION="$(git -C "$REPO_DIR" rev-parse HEAD)"
if [ "$ACTUAL_REVISION" != "$EXPECTED_REVISION" ]; then
  echo "Wrong source revision: $ACTUAL_REVISION" >&2
  exit 1
fi

python3 -m venv "$BUILD_DIR/venv"
"$BUILD_DIR/venv/bin/python" -m pip install --disable-pip-version-check \
  pyinstaller==6.16.0 \
  -r "$REPO_DIR/desktop/requirements-sidecar.txt"

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
OUTPUT_PATH="$DOWNLOADS_DIR/Pocket-i-$APP_VERSION-$(uname -m)-$SHORT_REVISION.dmg"
if [ -e "$OUTPUT_PATH" ]; then
  echo "Refusing to overwrite: $OUTPUT_PATH" >&2
  exit 1
fi
cp "$DMG_PATH" "$OUTPUT_PATH"
shasum -a 256 "$OUTPUT_PATH"
echo "DMG_READY: $OUTPUT_PATH"
cleanup
trap - EXIT
echo "TEMP_BUILD_REMOVED"
open -R "$OUTPUT_PATH"
