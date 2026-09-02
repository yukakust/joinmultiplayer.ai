#!/usr/bin/env bash
set -euo pipefail

EXPECTED_REVISION="cd060cb3cb0a7712ca9d75c6667a0f490a5666d5"
PYTHON_PATH="$HOME/.local/share/pocket-i-gate16a/bin/python"

if [ "$(uname -s)" != "Darwin" ]; then
  echo "This private A/B runner currently targets the owner's macOS setup." >&2
  exit 1
fi
if [ ! -x "$PYTHON_PATH" ]; then
  echo "The existing Pocket i local-search Python environment was not found." >&2
  exit 1
fi

RUN_DIR="$(mktemp -d "$HOME/Downloads/pocket-i-phrase-ab.XXXXXX")"
cleanup() {
  if [ -d "$RUN_DIR" ]; then
    rm -rf -- "$RUN_DIR"
  fi
}
trap cleanup EXIT

git clone -q --depth 50 --branch agent/game-loop-v0.1 \
  https://github.com/yukakust/joinmultiplayer.ai.git "$RUN_DIR/repo"
git -C "$RUN_DIR/repo" checkout -q --detach "$EXPECTED_REVISION"
if [ "$(git -C "$RUN_DIR/repo" rev-parse HEAD)" != "$EXPECTED_REVISION" ]; then
  echo "The A/B runner checked out the wrong source revision." >&2
  exit 1
fi

"$PYTHON_PATH" \
  "$RUN_DIR/repo/site/experiments/E007/phrase-search-ab-v0.1.py" \
  --output-dir "$HOME/Downloads"

cleanup
trap - EXIT
