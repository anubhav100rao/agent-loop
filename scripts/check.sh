#!/bin/sh
# Preflight: deps installed, exactly one test failing, MCP server lists 3 tools.
cd "$(dirname "$0")/.." || exit 1
[ -f .env ] && { set -a; . ./.env; set +a; }   # OPENROUTER_API_KEY, MODEL
PY=.venv/bin/python
fail() { echo "FAIL: $1"; exit 1; }

[ -x "$PY" ] || fail "no .venv (see README setup)"
$PY -c "import mcp, openai, pytest" 2>/dev/null || fail "python deps missing"
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

$PY -c "import phoenix.otel, openinference.instrumentation.openai" 2>/dev/null || fail "Phoenix deps missing"
echo "ok: Phoenix deps installed"
if curl -s -o /dev/null http://127.0.0.1:6006; then echo "ok: Phoenix running at http://127.0.0.1:6006"
else echo "WARN: Phoenix not running (start scripts/phoenix.sh in another tab)"; fi

[ -n "$OPENROUTER_API_KEY" ] || echo "WARN: OPENROUTER_API_KEY not set (put it in .env, see .env.example)"
echo "READY"
