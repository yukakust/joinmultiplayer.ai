#!/usr/bin/env bash
# Multiplayer — uninstaller. Removes everything the installer added.
#
#   curl -sSL https://joinmultiplayer.ai/uninstall.sh | sh
#
# Reversible by design: no sudo, everything lives under your home dir. This is
# best-effort (no `set -e`) — it keeps going and removes as much as it can even
# if one step is already gone.

INSTALL_DIR="$HOME/.gpu"

bold()  { printf "\033[1m%s\033[0m\n" "$*"; }
green() { printf "\033[32m%s\033[0m\n" "$*"; }
dim()   { printf "\033[2m%s\033[0m\n" "$*"; }

bold "◉ Multiplayer uninstaller — removing everything (no sudo needed)"
echo ""

# 1. Claude Code MCP
if command -v claude >/dev/null 2>&1; then
  if claude mcp remove gpu >/dev/null 2>&1; then
    green "✓ removed 'gpu' MCP from Claude Code"
  else
    dim "(no 'gpu' MCP in Claude Code)"
  fi
fi

# 2. Codex MCP block
CODEX_CFG="$HOME/.codex/config.toml"
if [ -f "$CODEX_CFG" ] && command -v python3 >/dev/null 2>&1; then
  if python3 - "$CODEX_CFG" <<'PYEOF'
import sys, re
p = sys.argv[1]; src = open(p).read()
open(p, 'w').write(re.sub(r'(?ms)^\[mcp_servers\.gpu\][^\[]*', '', src))
PYEOF
  then green "✓ removed 'gpu' MCP from Codex"; fi
fi

# 3. Background menu-bar app (LaunchAgent) — only present on tray installs
PLIST="$HOME/Library/LaunchAgents/com.gpu.menubar.plist"
if [ -f "$PLIST" ]; then
  uid="$(id -u)"
  launchctl bootout "gui/$uid" "$PLIST" 2>/dev/null || launchctl unload "$PLIST" 2>/dev/null || true
  rm -f "$PLIST"
  green "✓ stopped + removed the menu-bar background app"
fi

# 4. /gpu slash command + prompt
rm -f "$HOME/.claude/commands/gpu.md" "$HOME/.codex/prompts/gpu.md" 2>/dev/null || true

# 5. Managed block in ~/.claude/CLAUDE.md (only the clearly-marked block)
GLOBAL_MD="$HOME/.claude/CLAUDE.md"
if [ -f "$GLOBAL_MD" ] && grep -q "gpu-shared-context:begin" "$GLOBAL_MD" 2>/dev/null && command -v python3 >/dev/null 2>&1; then
  if python3 - "$GLOBAL_MD" <<'PYEOF'
import sys, re
p = sys.argv[1]; src = open(p).read()
out = re.sub(r'\n*<!-- gpu-shared-context:begin.*?gpu-shared-context:end -->\n*', '\n', src, flags=re.S)
open(p, 'w').write(out)
PYEOF
  then green "✓ removed the managed note from ~/.claude/CLAUDE.md"; fi
fi

# 6. Everything else (creds, downloaded MCP, preferences)
rm -rf "$INSTALL_DIR"
green "✓ removed $INSTALL_DIR"

echo ""
bold "✓ Done — Multiplayer fully removed. Start a new agent session to drop the tools."
dim "  (Your identity stays on the network; re-run the installer anytime to rejoin.)"
