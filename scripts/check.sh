#!/bin/sh
# Preflight: deps installed, exactly one test failing, MCP server lists 3 tools.
cd "$(dirname "$0")/.." || exit 1
PY=.venv/bin/python
fail() { echo "FAIL: $1"; exit 1; }

[ -x "$PY" ] || fail "no .venv (see README setup)"
$PY -c "import mcp, anthropic, pytest" 2>/dev/null || fail "python deps missing"
[ -x .venv/bin/claude-tap ] || fail "claude-tap not installed"
command -v claude >/dev/null || fail "claude CLI not on PATH"
echo "ok: deps installed"

summary=$($PY -m pytest shop -q 2>&1 | tail -1)
case "$summary" in
  "1 failed, 4 passed"*) echo "ok: tests: $summary" ;;
  *) fail "expected '1 failed, 4 passed', got '$summary' (run scripts/reset.sh)" ;;
esac

tools=$($PY scripts/list_mcp_tools.py 2>/dev/null | sort | tr '\n' ' ')
[ "$tools" = "add_comment get_ticket list_recent_deploys " ] \
  || fail "MCP server tools: '$tools'"
echo "ok: tracker MCP server lists 3 tools"

[ "$(cat mock_mcp/comments.json)" = "[]" ] || fail "comments not empty (run scripts/reset.sh)"
echo "ok: ticket comments empty"

[ -n "$ANTHROPIC_API_KEY" ] || echo "WARN: ANTHROPIC_API_KEY not set (nano_agent.py needs it)"
echo "READY"
