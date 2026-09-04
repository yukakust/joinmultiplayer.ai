#!/usr/bin/env bash
set -euo pipefail

EXPECTED_REVISION="ea850208c1c61c8a1270f1232833da94fd340c61"
SHORT_REVISION="ea85020"

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
BUILD_DIR="$(mktemp -d "$DOWNLOADS_DIR/pocket-i-checkpoint7v-build.XXXXXX")"
REPO_DIR="$BUILD_DIR/joinmultiplayer.ai"
cleanup() {
  if [ -d "$BUILD_DIR" ]; then
    rm -rf -- "$BUILD_DIR"
  fi
}
trap cleanup EXIT

echo "Building Pocket i with explicit brain selection from: $SHORT_REVISION"
git clone -q --depth 80 --branch agent/game-loop-v0.1 \
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
echo "Preparing local checks and the thin desktop runtime..."
CSC_IDENTITY_AUTO_DISCOVERY=false \
POCKET_I_BUILD_PYTHON="$BUILD_DIR/venv/bin/python" \
  ./build-current-platform.sh

ASAR_PATH="$(find "$REPO_DIR/desktop/app/dist" -type f -path '*.app/Contents/Resources/app.asar' -print -quit)"
if [ -z "$ASAR_PATH" ]; then
  echo "The packaged app.asar was not found." >&2
  exit 1
fi
for packed_module in audit-store.cjs evidence.cjs reranker.cjs remote-inference.cjs secret-scan.cjs setup.cjs; do
  if ! npx asar list "$ASAR_PATH" | grep -qx "/$packed_module"; then
    echo "The packaged application is missing $packed_module." >&2
    exit 1
  fi
done

node - <<NODE
const fs = require("node:fs");
const manifest = require("$REPO_DIR/desktop/app/model-manifest.json");
const setup = fs.readFileSync("$REPO_DIR/desktop/app/setup.cjs", "utf8");
const renderer = fs.readFileSync("$REPO_DIR/desktop/app/renderer/app.js", "utf8");
const html = fs.readFileSync("$REPO_DIR/desktop/app/renderer/index.html", "utf8");
if (!manifest.remoteBrain?.enabled) process.exit(2);
if (!manifest.remoteBrain.readerUrl.includes("yukabox.tail1e1ad1.ts.net")) process.exit(3);
if (!manifest.remoteBrain.relevanceUrl.includes("yukabox.tail1e1ad1.ts.net")) process.exit(4);
if (!setup.includes("brain-mode.json")) process.exit(5);
if (!html.includes('id="choose-yukabox"') || !html.includes('id="choose-local"')) process.exit(6);
if (!html.includes('id="open-test-log"')) process.exit(7);
if (!renderer.includes("renderBrainChoice")) process.exit(8);
NODE
echo "PACKAGED_BRAIN_CHOOSER_AND_TEST_LOGS_OK"

APP_VERSION="$(node -p "require('$REPO_DIR/desktop/app/package.json').version")"
if [ "$APP_VERSION" != "0.1.0-alpha.27" ]; then
  echo "Wrong package version: $APP_VERSION" >&2
  exit 1
fi
DMG_PATH="$(find "$REPO_DIR/desktop/app/dist" -maxdepth 1 -type f -name '*.dmg' -print -quit)"
if [ -z "$DMG_PATH" ]; then
  echo "The build finished without a DMG." >&2
  exit 1
fi
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
