#!/usr/bin/env bash
# Multiplayer — one-command installer for Claude Code + Codex.
#
# Open self-join, no password:
#      curl -sSL https://joinmultiplayer.ai/install.sh | sh
#
# It mints a fresh identity + token via the open /join, downloads the MCP, and
# registers it with Claude Code AND Codex. An agent can run it directly — there
# is nothing to type. Optional: pre-set BRAIN_USER to request a handle, or
# BRAIN_SHARE_ROOTS to choose which folders are shareable.
set -e

BRAIN_URL="${BRAIN_URL:-https://joinmultiplayer.ai}"
INSTALL_DIR="$HOME/.gpu"
# Filename must NOT be `mcp.py` — that shadows the installed `mcp` package
# when Python adds the script's dir to sys.path.
MCP_FILE="$INSTALL_DIR/gpu_mcp.py"

bold()  { printf "\033[1m%s\033[0m\n" "$*"; }
green() { printf "\033[32m%s\033[0m\n" "$*"; }
red()   { printf "\033[31m%s\033[0m\n" "$*"; }

# Interactive only with a real terminal (NOT under `curl | sh`, and not when a
# credential is already supplied).
NON_INTERACTIVE=""
[ -t 0 ] || NON_INTERACTIVE=1
[ -n "$BRAIN_PASSWORD" ] && NON_INTERACTIVE=1

bold "◉ Multiplayer installer"
echo ""

# Identity + credential.
#  - OPEN SELF-JOIN (default): no BRAIN_PASSWORD → mint a fresh identity + token
#    via the network's open /join. No password, no invite, no registration.
#  - Explicit / team: caller sets BRAIN_PASSWORD (+ BRAIN_USER). Used as-is.
if [ -z "$BRAIN_PASSWORD" ]; then
  bold "Joining Multiplayer — open self-join (no password)…"
  # Up to 2 attempts: a rate-limit hiccup (CF 429, ~10s window) or transient
  # blip self-heals on one retry, so the user never sees a failure.
  _want="${BRAIN_USER:-}"
  _try=0
  while [ "$_try" -lt 2 ]; do
    JOIN_RESP="$(curl -sSL --fail -X POST "$BRAIN_URL/join" \
        -H 'content-type: application/json' \
        -d "{\"handle\":\"$_want\"}" 2>/dev/null || true)"
    BRAIN_USER="$(printf '%s' "$JOIN_RESP" | sed -n 's/.*"user"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')"
    BRAIN_PASSWORD="$(printf '%s' "$JOIN_RESP" | sed -n 's/.*"token"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')"
    [ -n "$BRAIN_PASSWORD" ] && [ -n "$BRAIN_USER" ] && break
    _try=$((_try + 1))
    [ "$_try" -lt 2 ] && { echo "  (network/rate-limit hiccup — retrying in 12s…)"; sleep 12; }
  done
  if [ -z "$BRAIN_PASSWORD" ] || [ -z "$BRAIN_USER" ]; then
    red "self-join failed (could not reach $BRAIN_URL/join). Check your connection and retry."; exit 1
  fi
  green "→ joined as: $BRAIN_USER (external tier — no password needed)"
else
  # Explicit credential provided (team / core).
  if [ -z "$BRAIN_USER" ] && [ -z "$NON_INTERACTIVE" ]; then
    printf "Your handle: "; read -r BRAIN_USER
  fi
  if [ -z "$BRAIN_USER" ]; then
    red "BRAIN_USER required when BRAIN_PASSWORD is set"; exit 1
  fi
  green "→ identity: $BRAIN_USER"
fi

# 3. Share roots
if [ -z "$NON_INTERACTIVE" ] && [ -z "$BRAIN_SHARE_ROOTS" ]; then
  printf "Share roots [default: %s/code,%s/Desktop]: " "$HOME" "$HOME"
  read -r BRAIN_SHARE_ROOTS
fi
BRAIN_SHARE_ROOTS="${BRAIN_SHARE_ROOTS:-$HOME/code,$HOME/Desktop}"
green "→ share roots: $BRAIN_SHARE_ROOTS"
echo ""

# 4. Detect absolute python path (launchctl has minimal PATH so /usr/bin/env
#    resolves to Apple's Python 3.9 where rumps isn't installed)
PYTHON_PATH="$(command -v python3 || true)"
if [ -z "$PYTHON_PATH" ]; then
  red "python3 not found in PATH — install Python 3.10+ first"; exit 1
fi
green "→ python: $PYTHON_PATH"
PYTHON_RUNTIME="$PYTHON_PATH"
VENV_DIR="$INSTALL_DIR/venv"

python_site_packages() {
  "$PYTHON_RUNTIME" - <<'PYEOF'
import sysconfig
print(sysconfig.get_paths().get("purelib", ""))
PYEOF
}

install_python_deps() {
  if [ "$PYTHON_RUNTIME" != "$PYTHON_PATH" ]; then
    "$PYTHON_RUNTIME" -m pip install --quiet "$@" >/dev/null
    return
  fi
  if "$PYTHON_RUNTIME" -m pip install --quiet --user "$@" >/dev/null 2>&1; then
    return
  fi
  echo "(user-site pip unavailable; using $VENV_DIR)"
  if [ ! -x "$VENV_DIR/bin/python" ]; then
    "$PYTHON_PATH" -m venv "$VENV_DIR"
  fi
  PYTHON_RUNTIME="$VENV_DIR/bin/python"
  "$PYTHON_RUNTIME" -m pip install --quiet --upgrade pip >/dev/null
  "$PYTHON_RUNTIME" -m pip install --quiet "$@" >/dev/null
  green "✓ python runtime: $PYTHON_RUNTIME"
}

find_python_app() {
  "$PYTHON_RUNTIME" - <<'PYEOF'
from pathlib import Path
import sys

candidates = []
exe = Path(sys.executable).resolve()
for parent in (exe.parent, *exe.parents):
    candidates.append(parent / "Resources" / "Python.app")
for raw in {sys.base_prefix, sys.prefix, sys.exec_prefix}:
    p = Path(raw).resolve()
    candidates.append(p / "Resources" / "Python.app")

seen = set()
for candidate in candidates:
    if candidate in seen:
        continue
    seen.add(candidate)
    if (candidate / "Contents" / "Info.plist").exists():
        print(candidate)
        raise SystemExit(0)
raise SystemExit(1)
PYEOF
}

plist_set_string() {
  plist="$1"; key="$2"; value="$3"
  /usr/libexec/PlistBuddy -c "Set :$key $value" "$plist" 2>/dev/null || \
    /usr/libexec/PlistBuddy -c "Add :$key string $value" "$plist"
}

plist_set_bool() {
  plist="$1"; key="$2"; value="$3"
  /usr/libexec/PlistBuddy -c "Set :$key $value" "$plist" 2>/dev/null || \
    /usr/libexec/PlistBuddy -c "Add :$key bool $value" "$plist"
}

write_gpu_icon() {
  resources_dir="$1"
  iconset="$INSTALL_DIR/gpu.iconset"
  mkdir -p "$resources_dir" "$iconset"
  "$PYTHON_RUNTIME" - "$iconset" <<'PYEOF'
from pathlib import Path
import struct
import sys
import zlib

out = Path(sys.argv[1])
sizes = [
    ("icon_16x16.png", 16), ("icon_16x16@2x.png", 32),
    ("icon_32x32.png", 32), ("icon_32x32@2x.png", 64),
    ("icon_128x128.png", 128), ("icon_128x128@2x.png", 256),
    ("icon_256x256.png", 256), ("icon_256x256@2x.png", 512),
    ("icon_512x512.png", 512), ("icon_512x512@2x.png", 1024),
]
glyphs = {
    "G": ["01110", "10000", "10000", "10111", "10001", "10001", "01110"],
    "P": ["11110", "10001", "10001", "11110", "10000", "10000", "10000"],
    "U": ["10001", "10001", "10001", "10001", "10001", "10001", "01110"],
}

def png(path: Path, width: int, height: int, pixels: bytes) -> None:
    def chunk(kind: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data)) + kind + data
            + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
        )
    raw = b"".join(
        b"\x00" + pixels[y * width * 4:(y + 1) * width * 4]
        for y in range(height)
    )
    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw, 9))
        + chunk(b"IEND", b"")
    )

def render(size: int) -> bytes:
    bg = (12, 15, 18, 255)
    accent = (81, 255, 169, 255)
    white = (245, 247, 250, 255)
    pixels = bytearray(bg * (size * size))
    radius = size * 0.22
    for y in range(size):
        for x in range(size):
            dx = min(x, size - 1 - x)
            dy = min(y, size - 1 - y)
            if dx < radius and dy < radius:
                if (radius - dx) ** 2 + (radius - dy) ** 2 > radius ** 2:
                    pixels[(y * size + x) * 4 + 3] = 0
    border = max(2, size // 24)
    for y in range(size):
        for x in range(size):
            if x < border or y < border or x >= size - border or y >= size - border:
                idx = (y * size + x) * 4
                if pixels[idx + 3]:
                    pixels[idx:idx + 4] = bytes(accent)

    cell = max(1, size // 18)
    gap = max(1, cell // 2)
    glyph_w = 5 * cell
    total_w = glyph_w * 3 + gap * 2
    start_x = (size - total_w) // 2
    start_y = (size - 7 * cell) // 2
    for gi, letter in enumerate("GPU"):
        color = accent if letter == "P" else white
        gx = start_x + gi * (glyph_w + gap)
        for row, pattern in enumerate(glyphs[letter]):
            for col, bit in enumerate(pattern):
                if bit != "1":
                    continue
                for yy in range(start_y + row * cell, start_y + (row + 1) * cell):
                    for xx in range(gx + col * cell, gx + (col + 1) * cell):
                        if 0 <= xx < size and 0 <= yy < size:
                            idx = (yy * size + xx) * 4
                            pixels[idx:idx + 4] = bytes(color)
    return bytes(pixels)

for name, size in sizes:
    png(out / name, size, size, render(size))
PYEOF
  if command -v iconutil >/dev/null 2>&1; then
    iconutil -c icns "$iconset" -o "$resources_dir/gpu.icns"
  else
    cp "$iconset/icon_512x512@2x.png" "$resources_dir/gpu.icns"
  fi
  rm -rf "$iconset"
}

install_macos_gpu_app() {
  GPU_APP="$INSTALL_DIR/gpu.app"
  PYTHON_APP="$(find_python_app || true)"
  if [ -z "$PYTHON_APP" ] || [ ! -d "$PYTHON_APP" ]; then
    red "Python.app bundle not found; menu bar will launch with python directly"
    return 1
  fi

  rm -rf "$GPU_APP"
  if command -v ditto >/dev/null 2>&1; then
    ditto "$PYTHON_APP" "$GPU_APP"
  else
    cp -R "$PYTHON_APP" "$GPU_APP"
  fi
  rm -rf "$GPU_APP/Contents/_CodeSignature" "$GPU_APP/Contents/CodeResources"

  plist="$GPU_APP/Contents/Info.plist"
  macos_dir="$GPU_APP/Contents/MacOS"
  old_exec="$(/usr/libexec/PlistBuddy -c 'Print :CFBundleExecutable' "$plist" 2>/dev/null || echo Python)"
  if [ -x "$macos_dir/$old_exec" ] && [ "$old_exec" != "gpu" ]; then
    mv "$macos_dir/$old_exec" "$macos_dir/gpu"
  fi
  if [ ! -x "$macos_dir/gpu" ]; then
    first_exec="$(find "$macos_dir" -maxdepth 1 -type f -perm -111 | head -1)"
    if [ -n "$first_exec" ]; then
      mv "$first_exec" "$macos_dir/gpu"
    fi
  fi

  plist_set_string "$plist" CFBundleExecutable gpu
  plist_set_string "$plist" CFBundleIdentifier social.gpu.menubar
  plist_set_string "$plist" CFBundleName gpu
  plist_set_string "$plist" CFBundleDisplayName gpu
  plist_set_string "$plist" CFBundleIconFile gpu.icns
  plist_set_bool "$plist" LSUIElement false
  write_gpu_icon "$GPU_APP/Contents/Resources"

  chmod +x "$GPU_APP/Contents/MacOS/gpu"
  codesign --force --deep --sign - "$GPU_APP" >/dev/null 2>&1 || true
  xattr -dr com.apple.quarantine "$GPU_APP" >/dev/null 2>&1 || true
  green "✓ macOS app bundle ready → $GPU_APP"
}

# Transitional /download fetch: prefer Bearer (per-user token / post-cutover), fall back
# to Basic team:PW while the Caddy basic_auth wall is still up. Auto-adapts across the
# admin=identity cutover — no flag-day. Usage: dl <url-path> <out-file>
dl() {
  curl -sSL --fail -H "Authorization: Bearer $BRAIN_PASSWORD" "$BRAIN_URL$1" -o "$2" 2>/dev/null && return 0
  curl -sSL --fail -u "team:$BRAIN_PASSWORD" "$BRAIN_URL$1" -o "$2"
}

# --- Supply-chain verification ------------------------------------------------
# Every file we download is sha256-checked against the published CHECKSUMS.txt.
# The PRIMARY source is the OPEN client mirror on GitHub — a different origin from
# joinmultiplayer.ai, so an attacker who controls ONLY joinmultiplayer.ai can't slip
# code past this; the origin is only a fallback. (Caveat: a network/MITM attacker who
# can selectively fail the github.com fetch could force the origin fallback — pinning
# the manifest hash is a planned future hardening.)
# Fail-closed: a checksum MISMATCH always aborts; if checksums can't be fetched at
# all, or no sha256 tool exists, we also abort (set MP_SKIP_VERIFY=1 to bypass).
CHECKSUMS_RAW="https://raw.githubusercontent.com/yukakust/joinmultiplayer.ai/main/CHECKSUMS.txt"
CHECKSUMS_FILE=""
fetch_checksums() {
  [ -n "$CHECKSUMS_FILE" ] && [ -s "$CHECKSUMS_FILE" ] && return 0
  _out="$(mktemp 2>/dev/null || echo "/tmp/mp-checksums.$$")"
  for _src in "$CHECKSUMS_RAW" "$BRAIN_URL/CHECKSUMS.txt"; do
    if curl -fsSL "$_src" -o "$_out" 2>/dev/null && [ -s "$_out" ]; then
      CHECKSUMS_FILE="$_out"; return 0
    fi
  done
  return 1
}
sha256_of() {  # $1 = file → lowercase hex (empty ONLY if no sha256 tool at all)
  if command -v shasum >/dev/null 2>&1; then shasum -a 256 "$1" 2>/dev/null | awk '{print $1}'
  elif command -v sha256sum >/dev/null 2>&1; then sha256sum "$1" 2>/dev/null | awk '{print $1}'
  elif command -v openssl >/dev/null 2>&1; then openssl dgst -sha256 "$1" 2>/dev/null | awk '{print $NF}'
  elif command -v python3 >/dev/null 2>&1; then python3 -c "import hashlib,sys;print(hashlib.sha256(open(sys.argv[1],'rb').read()).hexdigest())" "$1" 2>/dev/null
  else echo ""; fi
}
verify() {  # $1 = published name (download filename)   $2 = local file
  [ "$MP_SKIP_VERIFY" = "1" ] && { red "⚠ MP_SKIP_VERIFY=1 — NOT verifying $1 (running unverified code is unsafe)"; return 0; }
  if ! fetch_checksums; then
    red "✗ could not fetch CHECKSUMS.txt — refusing to install unverified code for $1."
    red "  retry, or re-run with MP_SKIP_VERIFY=1 to bypass at your own risk."; exit 1
  fi
  _want="$(awk -v n="$1" '$2==n{print $1}' "$CHECKSUMS_FILE")"
  if [ -z "$_want" ]; then
    red "✗ no published checksum for $1 — refusing (MP_SKIP_VERIFY=1 to bypass)."; exit 1
  fi
  _got="$(sha256_of "$2")"
  if [ -z "$_got" ]; then
    red "✗ no sha256 tool (shasum/sha256sum/openssl/python3) to verify $1 — refusing."
    red "  install one, or re-run with MP_SKIP_VERIFY=1 to bypass at your own risk."; exit 1
  fi
  if [ "$_got" != "$_want" ]; then
    red "✗ CHECKSUM MISMATCH for $1 — the download does NOT match the open repo. Aborting."
    red "  expected $_want"
    red "  got      $_got"
    red "  Do NOT trust this. Report at github.com/yukakust/joinmultiplayer.ai/issues"; exit 1
  fi
  green "✓ verified $1 (sha256)"
}

# 5. Download MCP
mkdir -p "$INSTALL_DIR"
echo "Downloading MCP server → $MCP_FILE"
dl "/download/mcp.py" "$MCP_FILE"
# Sanity check: file should be > 1 KB and start with the python shebang or import
if [ ! -s "$MCP_FILE" ] || [ "$(wc -c < "$MCP_FILE")" -lt 1000 ]; then
  red "MCP file looks corrupted (too small) — check server, see $MCP_FILE"; exit 1
fi
verify "mcp.py" "$MCP_FILE"
chmod +x "$MCP_FILE"
green "✓ downloaded ($(wc -c < "$MCP_FILE") bytes)"

# 5b. Download agent_workspace helper (Step A+ — used by MCP and tray)
echo "Downloading agent-workspace helper → $INSTALL_DIR/agent_workspace.py"
if dl "/download/agent_workspace.py" "$INSTALL_DIR/agent_workspace.py"; then
  verify "agent_workspace.py" "$INSTALL_DIR/agent_workspace.py"
  green "✓ agent_workspace.py ready"
else
  red "(agent_workspace.py download failed — auto-react features will be skipped)"
fi

# 5c. Download the Shared-Room watcher (self-updating: it auto-refreshes itself
# from /download/room_agent.py thereafter — each refresh is sha256-verified against
# CHECKSUMS.txt before it's applied, so this is the only manual fetch ever).
echo "Downloading Shared-Room watcher → $INSTALL_DIR/room_agent.py"
if dl "/download/room_agent.py" "$INSTALL_DIR/room_agent.py"; then
  verify "room_agent.py" "$INSTALL_DIR/room_agent.py"
  green "✓ room_agent.py ready"
else
  red "(room_agent.py download failed — Shared Room watcher will be skipped)"
fi

# 6. Python deps — use absolute python -m pip (NOT --upgrade, preserves user pins)
echo "Installing Python deps (mcp, requests)…"
install_python_deps mcp requests
green "✓ deps installed"

# 7. Claude Code — use absolute python path so MCP subprocess finds the right deps
if command -v claude >/dev/null 2>&1; then
  claude mcp remove gpu >/dev/null 2>&1 || true
  claude mcp add gpu --scope user \
    -e "BRAIN_URL=$BRAIN_URL" \
    -e "BRAIN_PASSWORD=$BRAIN_PASSWORD" \
    -e "BRAIN_USER=$BRAIN_USER" \
    -e "BRAIN_SHARE_ROOTS=$BRAIN_SHARE_ROOTS" \
    -- "$PYTHON_RUNTIME" "$MCP_FILE" >/dev/null
  green "✓ Claude Code: added 'gpu' MCP"
else
  echo "(Claude Code CLI not found; skipping)"
fi

# 8. Codex — also use absolute python path
CODEX_CFG="$HOME/.codex/config.toml"
if [ -d "$HOME/.codex" ] || command -v codex >/dev/null 2>&1; then
  mkdir -p "$HOME/.codex"
  if [ -f "$CODEX_CFG" ]; then
    "$PYTHON_RUNTIME" - "$CODEX_CFG" <<'PYEOF' || true
import sys, re
p = sys.argv[1]; src = open(p).read()
open(p, 'w').write(re.sub(r'(?ms)^\[mcp_servers\.gpu\][^\[]*', '', src))
PYEOF
  fi
  cat >> "$CODEX_CFG" <<EOF

[mcp_servers.gpu]
command = "$PYTHON_RUNTIME"
args = ["$MCP_FILE"]
env = { BRAIN_URL = "$BRAIN_URL", BRAIN_PASSWORD = "$BRAIN_PASSWORD", BRAIN_USER = "$BRAIN_USER", BRAIN_SHARE_ROOTS = "$BRAIN_SHARE_ROOTS" }
EOF
  green "✓ Codex: added 'gpu' MCP ($CODEX_CFG)"
else
  echo "(Codex not found; skipping)"
fi

# 8.5 Any MCP client with a JSON config (Cursor, Windsurf, Claude Desktop, Antigravity, …) —
# same MCP, same env. People use different agents, so register everywhere we can find a client.
# Merge-preserves other servers; only touches a client whose marker dir exists.
add_json_mcp() {  # $1 = config file path   $2 = client marker dir (skip unless it exists)
  [ -d "$2" ] || return 0
  "$PYTHON_RUNTIME" - "$1" "$PYTHON_RUNTIME" "$MCP_FILE" "$BRAIN_URL" "$BRAIN_PASSWORD" "$BRAIN_USER" "$BRAIN_SHARE_ROOTS" <<'PYEOF' || return 0
import sys, json, os
cfg, py, mcp, url, pw, user, roots = sys.argv[1:8]
d = {}
if os.path.exists(cfg):
    try: d = json.load(open(cfg)) or {}
    except Exception: d = {}
d.setdefault("mcpServers", {})["gpu"] = {
    "command": py, "args": [mcp],
    "env": {"BRAIN_URL": url, "BRAIN_PASSWORD": pw, "BRAIN_USER": user, "BRAIN_SHARE_ROOTS": roots},
}
os.makedirs(os.path.dirname(cfg), exist_ok=True)
json.dump(d, open(cfg, "w"), indent=2)
PYEOF
  green "✓ MCP registered → $1"
}
add_json_mcp "$HOME/.cursor/mcp.json"                                                "$HOME/.cursor"                                  # Cursor
add_json_mcp "$HOME/.codeium/windsurf/mcp_config.json"                               "$HOME/.codeium"                                # Windsurf
add_json_mcp "$HOME/.antigravity/mcp.json"                                           "$HOME/.antigravity"                            # Antigravity (Google)
add_json_mcp "$HOME/Library/Application Support/Claude/claude_desktop_config.json"   "$HOME/Library/Application Support/Claude"       # Claude Desktop (macOS)
add_json_mcp "$HOME/.config/Claude/claude_desktop_config.json"                       "$HOME/.config/Claude"                          # Claude Desktop (Linux)
add_json_mcp "$HOME/.config/Cursor/mcp.json"                                         "$HOME/.config/Cursor"                          # Cursor (Linux)
# Escape hatch — any other client: MP_EXTRA_MCP_CONFIGS="/path/a.json /path/b.json"
[ -n "$MP_EXTRA_MCP_CONFIGS" ] && for _c in $MP_EXTRA_MCP_CONFIGS; do add_json_mcp "$_c" "$(dirname "$_c")"; done

# 8.6 Room-agent slash command (/gpu) — makes this install a Shared-Room agent
# out of the box. Runs in the user's live, logged-in Claude Code / Codex session
# (no token, no daemon) and uses the gpu MCP room tools to propose plans and do
# the user's assigned areas. Installed for whichever CLIs are present.
install_gpu_command() {
  cmd_dir="$1"
  mkdir -p "$cmd_dir"
  cat > "$cmd_dir/gpu.md" <<'GPUCMD'
---
description: Act as my gpu Shared-Room agent — propose plans for new projects and do my assigned areas (uses the gpu MCP room tools).
---

You are my **gpu Shared-Room agent**. Do ONE pass over the team rooms using the gpu MCP room tools (`room_list`, `room_get`, `room_suggest_owners`, `room_propose`, `room_stream`, `room_tail`, `room_my_work`, `room_alarm`, `room_steal`), then stop and report. Single shot — not a loop.

## 1 — Propose plans for new projects
Call `room_list`. For each room with status "drafting" that has no areas yet:
- `room_get` it to read the goal.
- Decompose the goal into 3–6 concrete areas (e.g. backend, frontend, design, memory, infra).
- `room_suggest_owners(room_id, areas)` for competency-based owners; for any area with no suggestion, assign by your knowledge of the people in this room and the goal.
- `room_propose(room_id, areas=[{"area": "...", "owner": "..."}, ...])` to set the draft.
- `room_stream(room_id, "Proposed plan: <area -> owner, ...>. Reply approve in this topic to lock it in.", kind="note")` so it shows in Telegram.
- Never call approve or start — that's the human's decision.

## 2 — Do the work assigned to me
Call `room_my_work`. For each area assigned to me in a "running" room:
- `room_tail(room_id)` first — skip the area if I already posted a done for it.
- Do the real, bounded work for that area. If it needs local files, work in the current directory.
- `room_stream(room_id, "<short progress>", area="<area>", kind="progress")` as you go; finish with `room_stream(..., kind="done")`.
- If you hit a blocker that affects others, `room_alarm(room_id, reason)`.

## 3 — Report
Tell me in 2-4 lines what you proposed and/or did, with room ids. Keep every Telegram-visible message short and in English.
GPUCMD
}

if command -v claude >/dev/null 2>&1 || [ -d "$HOME/.claude" ]; then
  install_gpu_command "$HOME/.claude/commands"
  green "✓ /gpu room-agent command installed for Claude Code"
fi
if command -v codex >/dev/null 2>&1 || [ -d "$HOME/.codex" ]; then
  install_gpu_command "$HOME/.codex/prompts"
  green "✓ /gpu room-agent prompt installed for Codex"
fi

# 8.7 Shared-context auto-share — a standing instruction so your interactive
# agent syncs the team room at start and proactively posts decisions/progress
# (the input side of the living shared context). Idempotent: only added once.
GLOBAL_MD="$HOME/.claude/CLAUDE.md"
if [ -f "$GLOBAL_MD" ] && grep -q "gpu-shared-context:begin" "$GLOBAL_MD" 2>/dev/null; then
  green "✓ gpu shared-context instruction already present"
else
  mkdir -p "$HOME/.claude"
  cat >> "$GLOBAL_MD" <<'MD'

<!-- gpu-shared-context:begin (managed by gpu install; safe to remove this block) -->
# gpu — shared team context (auto-share)

You may be a member of a shared room on Multiplayer. People coordinate through each
person's own agent over a shared backplane — not by DMing each other. When a shared
room is relevant to what we're working on:
- Sync at the start of a session: `mcp__gpu__room_list` → find the active team room (most
  recent running) → `mcp__gpu__room_tail` it to load the latest team context.
- Auto-share as you work: when you and I make a team-relevant decision, change direction,
  or hit notable progress, post it to that room right away:
  `mcp__gpu__room_stream(room_id, "DECISION: …" or "PROGRESS: …", kind="note")`. Don't wait
  to be asked, and don't DM teammates — the room is the channel; their agents react.
- Keep me in the loop: if a teammate's change needs my call, surface it to me.
If none of this is relevant to the current work, ignore it. Keep room posts short, English.

# Multiplayer — reveal new abilities at milestones (tell them RIGHT AWAY)
Watch your Multiplayer inbox: a `friend_accepted` event (or a newly-accepted friend in
your friends list) means a NEW ability just unlocked for the human — tell them the
MOMENT you notice it, ONCE, briefly, in their language. Don't make them wait or ask.
- FIRST accepted friend → friend-tier abilities (request a file or command from that
  friend's agent, with their approval; hand off a task to them);
- create or join a TEAM → team abilities (shared project rooms with plan->approve->work,
  delegate, request compute, the team knowledge vault).
Don't repeat a milestone you've already announced. When the user names a person
("message Vitalik"), resolve it to the right handle from their friends list.
<!-- gpu-shared-context:end -->
MD
  green "✓ gpu shared-context auto-share instruction installed (~/.claude/CLAUDE.md)"
fi

# 8.5 Agent preference (which CLI gpu spawns headless for auto-actions)
HAVE_CLAUDE=0; HAVE_CODEX=0
command -v claude >/dev/null 2>&1 && HAVE_CLAUDE=1
command -v codex  >/dev/null 2>&1 && HAVE_CODEX=1
AGENT_PREFERRED=""
if [ $HAVE_CLAUDE -eq 1 ] && [ $HAVE_CODEX -eq 1 ]; then
  if [ -z "$NON_INTERACTIVE" ]; then
    echo ""
    echo "Both Claude Code and Codex are installed. When gpu auto-reacts to"
    echo "incoming requests (Step A+ — coming online), which agent should it"
    echo "spawn headless on your behalf?"
    printf "  1) claude  (Anthropic, default)\n  2) codex   (OpenAI)\nPick [1/2 or claude/codex]: "
    read -r AGENT_CHOICE
    case "$AGENT_CHOICE" in
      2|codex)  AGENT_PREFERRED="codex" ;;
      *)        AGENT_PREFERRED="claude" ;;
    esac
  else
    AGENT_PREFERRED="claude"
  fi
elif [ $HAVE_CLAUDE -eq 1 ]; then
  AGENT_PREFERRED="claude"
elif [ $HAVE_CODEX -eq 1 ]; then
  AGENT_PREFERRED="codex"
else
  AGENT_PREFERRED="claude"  # placeholder; user can install either later
fi
mkdir -p "$INSTALL_DIR"
# Seed (or refresh just this key in) preferences.json
"$PYTHON_RUNTIME" - "$INSTALL_DIR/preferences.json" "$AGENT_PREFERRED" <<'PYEOF'
import json, os, sys
p, agent = sys.argv[1], sys.argv[2]
data = {}
if os.path.exists(p):
    try: data = json.load(open(p))
    except: data = {}
defaults = {
    "agent_preferred": agent,
    "auto_react_for_trusted_when_closed": True,
    "max_daily_auto_runs": 50,
    "inbox_mode": "tier_gated",
    "vault_access_for_bubbles": "public_profile_only",
}
merged = {**defaults, **data, "agent_preferred": agent}
open(p, 'w').write(json.dumps(merged, indent=2, ensure_ascii=False))
os.chmod(p, 0o600)
PYEOF
green "✓ preferences saved → $INSTALL_DIR/preferences.json (agent_preferred=$AGENT_PREFERRED)"

# 9. Persist agent.json (used by menu bar app — keeps creds in one place)
# Named agent.json (not config.json) to avoid collision with gpu.social signup tool's ~/.gpu/config.json
cat > "$INSTALL_DIR/agent.json" <<EOF
{
  "BRAIN_URL": "$BRAIN_URL",
  "BRAIN_PASSWORD": "$BRAIN_PASSWORD",
  "BRAIN_USER": "$BRAIN_USER",
  "BRAIN_SHARE_ROOTS": "$BRAIN_SHARE_ROOTS"
}
EOF
chmod 600 "$INSTALL_DIR/agent.json"
green "✓ config saved → $INSTALL_DIR/agent.json"

# 10. Menu bar app — macOS only, OPT-IN (default OFF). Multiplayer runs entirely
# inside your coding agent; we do NOT add an always-on background app or a login
# item unless you ask for one. Enable a menu-bar status icon with MP_MENUBAR=1.
if [ "$(uname)" = "Darwin" ] && [ "$MP_MENUBAR" = "1" ]; then
  echo ""
  echo "Installing menu bar app (MP_MENUBAR=1)…"
  dl "/download/menu_bar.py" "$INSTALL_DIR/menu_bar.py" || true
  if [ ! -s "$INSTALL_DIR/menu_bar.py" ] || [ "$(wc -c < "$INSTALL_DIR/menu_bar.py")" -lt 500 ]; then
    red "menu_bar.py download failed (file too small); skipping menu bar"
  else
    verify "menu_bar.py" "$INSTALL_DIR/menu_bar.py"
    install_python_deps rumps
    PY_SITE="$(python_site_packages)"
    GPU_APP="$INSTALL_DIR/gpu.app"
    USE_GPU_APP=""
    if install_macos_gpu_app; then
      USE_GPU_APP=1
    fi

    PLIST="$HOME/Library/LaunchAgents/com.gpu.menubar.plist"
    mkdir -p "$HOME/Library/LaunchAgents"
    if [ -n "$USE_GPU_APP" ]; then
      cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key><string>com.gpu.menubar</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/open</string>
        <string>-W</string>
        <string>-a</string>
        <string>$GPU_APP</string>
        <string>--args</string>
        <string>$INSTALL_DIR/menu_bar.py</string>
    </array>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key><string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
        <key>PYTHONPATH</key><string>$PY_SITE</string>
    </dict>
    <key>RunAtLoad</key><true/>
    <key>KeepAlive</key><true/>
    <key>StandardOutPath</key><string>$INSTALL_DIR/menu_bar.log</string>
    <key>StandardErrorPath</key><string>$INSTALL_DIR/menu_bar.log</string>
</dict>
</plist>
EOF
    else
      # CRITICAL: use absolute python path. launchctl has minimal PATH so
      # /usr/bin/env python3 resolves to Apple system Python 3.9 where rumps isn't installed.
      cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key><string>com.gpu.menubar</string>
    <key>ProgramArguments</key>
    <array>
        <string>$PYTHON_RUNTIME</string>
        <string>$INSTALL_DIR/menu_bar.py</string>
    </array>
    <key>RunAtLoad</key><true/>
    <key>KeepAlive</key><true/>
    <key>StandardOutPath</key><string>$INSTALL_DIR/menu_bar.log</string>
    <key>StandardErrorPath</key><string>$INSTALL_DIR/menu_bar.log</string>
</dict>
</plist>
EOF
    fi
    uid="$(id -u)"
    launchctl bootout "gui/$uid" "$PLIST" 2>/dev/null || launchctl unload "$PLIST" 2>/dev/null || true
    launchctl bootstrap "gui/$uid" "$PLIST" 2>/dev/null || launchctl load -w "$PLIST"
    launchctl kickstart -k "gui/$uid/com.gpu.menubar" 2>/dev/null || true
    green "✓ menu bar app started — look for the gpu app and ◉ in the menu bar"
  fi
elif [ "$(uname)" = "Darwin" ]; then
  echo ""
  echo "(No menu-bar app or login item installed — Multiplayer lives inside your agent."
  echo " Want a status icon that starts at login? re-run with MP_MENUBAR=1.)"
fi

# First-run marker: the MCP self-heals the one-time portrait step from this on next start
# (decoupled from the CLAUDE.md note, which can silently fail). See mcp.py FIRST-RUN ONBOARDING.
: > "$INSTALL_DIR/onboarding_pending" 2>/dev/null || true

echo ""
bold "✓ Done! One last step, and it's the only thing you do by hand:"
echo "  fully quit your coding agent (Claude Code / Codex) and open it again."
echo "  That's what switches the new Multiplayer tools on. Nothing else on your"
echo "  machine changes — no background app, no login item, no system settings."
echo ""
echo "Then try in chat:"
echo "  who's online on Multiplayer?"
echo "  who knows <topic>?            # ask the network"
echo "  add <name> as a friend         # connect 1:1"
echo ""
echo "Your network grows by word of mouth — get someone you work with on it:"
echo "  tell them to say 'joinmultiplayer.ai' to their own agent."
echo ""
echo "Shared Room: type /gpu to act as a room-agent — it proposes plans for new"
echo "  projects and does your assigned areas alongside the people you connect with."
