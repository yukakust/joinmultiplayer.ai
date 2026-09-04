#!/usr/bin/env bash
set -euo pipefail

if [ "$(uname -s)" != "Darwin" ]; then
  echo "This cleanup is only for the owner's macOS build machine." >&2
  exit 1
fi

FAILED_BUILD="$HOME/Downloads/pocket-i-checkpoint7p-build.8T4nuw"
PYINSTALLER_CACHE="$HOME/Library/Application Support/pyinstaller"

echo "Free space before:"
df -h "$HOME" | tail -1

for target in "$FAILED_BUILD" "$PYINSTALLER_CACHE"; do
  if [ -e "$target" ]; then
    du -sh "$target"
    rm -rf -- "$target"
    echo "Removed generated build data: $target"
  else
    echo "Already absent: $target"
  fi
done

echo "Free space after:"
df -h "$HOME" | tail -1
echo "CLEANUP_COMPLETE"
