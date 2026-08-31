#!/usr/bin/env bash
set -euo pipefail

APP_DIR="$(cd "$(dirname "$0")" && pwd)"
DESKTOP_DIR="$(cd "$APP_DIR/.." && pwd)"
REPO_DIR="$(cd "$DESKTOP_DIR/.." && pwd)"
PYTHON_BIN="${POCKET_I_BUILD_PYTHON:-$REPO_DIR/.venv/bin/python}"

if ! "$PYTHON_BIN" -c 'import PyInstaller' >/dev/null 2>&1; then
  echo "PyInstaller is missing from $PYTHON_BIN" >&2
  exit 1
fi

rm -rf "$APP_DIR/sidecar-current" "$APP_DIR/build-sidecar"
mkdir -p "$APP_DIR/sidecar-current" "$APP_DIR/build-sidecar"

"$PYTHON_BIN" -m PyInstaller \
  --noconfirm \
  --clean \
  --onefile \
  --name pocket-i-core \
  --paths "$DESKTOP_DIR" \
  --distpath "$APP_DIR/sidecar-current" \
  --workpath "$APP_DIR/build-sidecar/work" \
  --specpath "$APP_DIR/build-sidecar" \
  "$DESKTOP_DIR/pocket_i_app/bridge.py"

cd "$APP_DIR"
case "$(uname -s)" in
  Linux) npm run dist:linux ;;
  Darwin) npm run dist:mac ;;
  *) echo "This checkpoint builds only Linux and macOS." >&2; exit 1 ;;
esac

