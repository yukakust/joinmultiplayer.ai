#!/usr/bin/env bash
set -euo pipefail

EXPECTED_REVISION="e3c980a8dfc2f1fa636dac6636647d672a1b1060"
SHORT_REVISION="e3c980a"
TOKEN_HOST="${POCKET_I_TOKEN_HOST:-yuka@yukabox.tail1e1ad1.ts.net}"
TOKEN_REMOTE_PATH="${POCKET_I_TOKEN_REMOTE_PATH:-.config/pocket-i/alpha-access/vitaly-alpha.token}"

if [ "$(uname -s)" != "Darwin" ]; then
  echo "This builder must run on macOS." >&2
  exit 1
fi
for command_name in git python3 npm node ssh; do
  command -v "$command_name" >/dev/null 2>&1 || { echo "$command_name is required." >&2; exit 1; }
done

DOWNLOADS_DIR="$HOME/Downloads"
mkdir -p "$DOWNLOADS_DIR"
BUILD_DIR="$(mktemp -d "$DOWNLOADS_DIR/pocket-i-vitaly-build.XXXXXX")"
REPO_DIR="$BUILD_DIR/joinmultiplayer.ai"
TOKEN_FILE="$BUILD_DIR/vitaly-alpha.token"
cleanup() {
  if [ -d "$BUILD_DIR" ]; then rm -rf -- "$BUILD_DIR"; fi
}
trap cleanup EXIT

echo "Preparing Vitaly's audited closed alpha build with reranker cutoff 0.05..."
umask 077
ssh -o BatchMode=yes -o ConnectTimeout=10 "$TOKEN_HOST" "cat '$TOKEN_REMOTE_PATH'" > "$TOKEN_FILE"
chmod 600 "$TOKEN_FILE"
TOKEN_LENGTH="$(tr -d '\r\n' < "$TOKEN_FILE" | wc -c | tr -d ' ')"
if [ "$TOKEN_LENGTH" -lt 32 ]; then
  echo "The closed-alpha access key could not be loaded." >&2
  exit 1
fi

git clone -q --depth 80 --branch main \
  https://github.com/yukakust/joinmultiplayer.ai.git "$REPO_DIR"
git -C "$REPO_DIR" checkout -q --detach "$EXPECTED_REVISION"
ACTUAL_REVISION="$(git -C "$REPO_DIR" rev-parse HEAD)"
if [ "$ACTUAL_REVISION" != "$EXPECTED_REVISION" ]; then
  echo "Wrong source revision: $ACTUAL_REVISION" >&2
  exit 1
fi

TOKEN_FILE="$TOKEN_FILE" REPO_DIR="$REPO_DIR" python3 - <<'PY'
import json
import os
from pathlib import Path

root = Path(os.environ["REPO_DIR"]) / "desktop" / "app"
manifest_path = root / "model-manifest.json"
manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
manifest["remoteBrain"].update({
    "enabled": True,
    "transport": "https",
    "label": "Yuka's Yukabox over HTTPS",
    "readerUrl": "https://brain.joinmultiplayer.ai/reader",
    "relevanceUrl": "https://brain.joinmultiplayer.ai/relevance",
})
manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
token = Path(os.environ["TOKEN_FILE"]).read_text(encoding="utf-8").strip()
(root / "remote-access.json").write_text(
    json.dumps({"schemaVersion": "pocket-i-remote-access-v0.1", "token": token}, indent=2) + "\n",
    encoding="utf-8",
)
PY

python3 -m venv "$BUILD_DIR/venv"
"$BUILD_DIR/venv/bin/python" -m pip install --disable-pip-version-check \
  pyinstaller==6.16.0 \
  -r "$REPO_DIR/desktop/requirements-sidecar.txt"

cd "$REPO_DIR"
PYTHONPATH=desktop "$BUILD_DIR/venv/bin/python" -m unittest discover -s desktop/tests -v
cd "$REPO_DIR/desktop/app"
npm ci
npm test
echo "Building the thin Mac app (models stay on Yukabox)..."
CSC_IDENTITY_AUTO_DISCOVERY=false \
POCKET_I_BUILD_PYTHON="$BUILD_DIR/venv/bin/python" \
  ./build-current-platform.sh

ASAR_PATH="$(find "$REPO_DIR/desktop/app/dist" -type f -path '*.app/Contents/Resources/app.asar' -print -quit)"
if [ -z "$ASAR_PATH" ]; then
  echo "The packaged app.asar was not found." >&2
  exit 1
fi
for packed_module in audit-store.cjs evidence.cjs reranker.cjs remote-inference.cjs remote-access.json secret-scan.cjs setup.cjs; do
  if ! npx asar list "$ASAR_PATH" | grep -qx "/$packed_module"; then
    echo "The packaged application is missing $packed_module." >&2
    exit 1
  fi
done

REPO_DIR="$REPO_DIR" node - <<'NODE'
const fs = require("node:fs");
const root = process.env.REPO_DIR + "/desktop/app";
const manifest = require(root + "/model-manifest.json");
const access = require(root + "/remote-access.json");
const reranker = fs.readFileSync(root + "/reranker.cjs", "utf8");
if (manifest.remoteBrain.transport !== "https") process.exit(2);
if (manifest.remoteBrain.readerUrl !== "https://brain.joinmultiplayer.ai/reader") process.exit(3);
if (manifest.remoteBrain.relevanceUrl !== "https://brain.joinmultiplayer.ai/relevance") process.exit(4);
if (!access.token || access.token.length < 32) process.exit(5);
if (!reranker.includes("const DROP_AT = 0.05;")) process.exit(6);
if (manifest.remoteBrain.auditMode !== "full") process.exit(7);
NODE

APP_VERSION="$(node -p "require('$REPO_DIR/desktop/app/package.json').version")"
if [ "$APP_VERSION" != "0.1.0-alpha.30" ]; then
  echo "Wrong package version: $APP_VERSION" >&2
  exit 1
fi
DMG_PATH="$(find "$REPO_DIR/desktop/app/dist" -maxdepth 1 -type f -name '*.dmg' -print -quit)"
if [ -z "$DMG_PATH" ]; then
  echo "The build finished without a DMG." >&2
  exit 1
fi
OUTPUT_PATH="$DOWNLOADS_DIR/Pocket-i-$APP_VERSION-Vitaly-$(uname -m)-$SHORT_REVISION.dmg"
if [ -e "$OUTPUT_PATH" ]; then
  echo "Refusing to overwrite: $OUTPUT_PATH" >&2
  exit 1
fi
cp "$DMG_PATH" "$OUTPUT_PATH"
shasum -a 256 "$OUTPUT_PATH"
echo "DMG_READY: $OUTPUT_PATH"
cleanup
trap - EXIT
open -R "$OUTPUT_PATH"
