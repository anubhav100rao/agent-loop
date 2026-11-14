#!/bin/sh
# Run nano_agent.py through claude-tap so its requests show in the dashboard.
# usage: scripts/nano_traced.sh "task"
cd "$(dirname "$0")/.." || exit 1
.venv/bin/claude-tap --tap-no-launch --tap-no-open --tap-client codex \
  --tap-target https://api.openai.com/v1 --tap-host 127.0.0.1 --tap-port 8788 \
  >/dev/null 2>&1 &
TAP=$!
trap 'kill $TAP 2>/dev/null' EXIT
sleep 3
OPENAI_BASE_URL=http://127.0.0.1:8788 .venv/bin/python nano_agent.py --verbose "$@"
echo
echo "trace: http://127.0.0.1:19527 (newest row, then Trace)"
