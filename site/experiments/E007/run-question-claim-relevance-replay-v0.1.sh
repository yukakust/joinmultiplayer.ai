#!/usr/bin/env bash
set -euo pipefail

EXPECTED_REVISION="79fa2a8deb4e98d1adc76bb4c789e8bc63aaa210"
RUN_DIR="$(mktemp -d "$HOME/Downloads/pocket-i-question-relevance.XXXXXX")"
trap 'rm -rf -- "$RUN_DIR"' EXIT

if [[ $# -ge 1 ]]; then
  INPUT="$1"
else
  INPUT="$(find "$HOME/Downloads" -maxdepth 1 -type f -name 'Pocket-i-fallback30-*-private.json' -print0 \
    | xargs -0 ls -t 2>/dev/null | head -n 1 || true)"
fi

if [[ -z "${INPUT:-}" || ! -f "$INPUT" ]]; then
  echo "Could not find the private checkpoint 7R JSON in Downloads." >&2
  echo "Pass its full path as the first argument." >&2
  exit 2
fi

git clone -q --depth 80 --branch agent/game-loop-v0.1 \
  https://github.com/yukakust/joinmultiplayer.ai.git "$RUN_DIR/repo"
git -C "$RUN_DIR/repo" checkout -q --detach "$EXPECTED_REVISION"

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUTPUT="$HOME/Downloads/Pocket-i-question-relevance-$STAMP-private.json"
node "$RUN_DIR/repo/site/experiments/E007/run-question-claim-relevance-replay-v0.1.cjs" \
  "$INPUT" "$OUTPUT"
