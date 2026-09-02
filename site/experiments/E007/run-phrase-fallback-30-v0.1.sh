#!/usr/bin/env bash
set -euo pipefail
EXPECTED_REVISION="2d45edbace224523fe84625bd9e6e2be62a397d3"
PY="$HOME/.local/share/pocket-i-gate16a/bin/python"
RUN="$(mktemp -d "$HOME/Downloads/pocket-i-fallback30.XXXXXX")"; trap 'rm -rf -- "$RUN"' EXIT
git clone -q --depth 60 --branch agent/game-loop-v0.1 https://github.com/yukakust/joinmultiplayer.ai.git "$RUN/repo"
git -C "$RUN/repo" checkout -q --detach "$EXPECTED_REVISION"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"; INPUT="$HOME/Downloads/Pocket-i-fallback30-$STAMP-private-input.json"; OUTPUT="$HOME/Downloads/Pocket-i-fallback30-$STAMP-private.json"
"$PY" "$RUN/repo/site/experiments/E007/prepare-phrase-fallback-30-v0.1.py" --output "$INPUT"
node "$RUN/repo/site/experiments/E007/run-phrase-fallback-30-v0.1.cjs" "$INPUT" "$OUTPUT"
