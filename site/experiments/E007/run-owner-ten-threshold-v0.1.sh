#!/usr/bin/env bash
set -euo pipefail

SOURCE_REF="261482e7d8b097ad8eeb186d476f5cc5e83b5df6"

if pgrep -x "Pocket i" >/dev/null 2>&1; then
  echo "Close Pocket i with Command-Q before this standalone test."
  exit 1
fi

TEST_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/pocket-i-threshold-005.XXXXXX")"
cleanup() { rm -rf "$TEST_ROOT"; }
trap cleanup EXIT

mkdir -p "$TEST_ROOT/repo"
curl -fsSL "https://github.com/yukakust/joinmultiplayer.ai/archive/${SOURCE_REF}.tar.gz" \
  -o "$TEST_ROOT/source.tar.gz"
tar -xzf "$TEST_ROOT/source.tar.gz" --strip-components=1 -C "$TEST_ROOT/repo"

node "$TEST_ROOT/repo/site/experiments/E007/run-owner-ten-threshold-v0.1.cjs"
