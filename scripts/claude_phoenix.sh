#!/bin/sh
# Start Claude Code with its built-in OpenTelemetry traces (beta) sent to Phoenix,
# project "claude-code". Spans go through scripts/claude_relay.py, which names
# them after the tool/model, fills input/output and tokens, and drops your email.
# Needs Claude Code 2.1.139+ and scripts/phoenix.sh running.
# usage: scripts/claude_phoenix.sh            (interactive, as in Act 1)
#        scripts/claude_phoenix.sh -p "task"  (headless)
cd "$(dirname "$0")/.." || exit 1
curl -s -o /dev/null http://127.0.0.1:6006 || { echo "Phoenix not running: scripts/phoenix.sh"; exit 1; }

if ! curl -s -o /dev/null http://127.0.0.1:6007; then  # start the relay unless one is running
  .venv/bin/python scripts/claude_relay.py > .claude_relay.log 2>&1 &
  RELAY=$!
  trap 'sleep 6; kill $RELAY 2>/dev/null' EXIT   # give the last span batch time to arrive
  sleep 1
fi

export CLAUDE_CODE_ENABLE_TELEMETRY=1 CLAUDE_CODE_ENHANCED_TELEMETRY_BETA=1
export OTEL_TRACES_EXPORTER=otlp OTEL_EXPORTER_OTLP_TRACES_PROTOCOL=http/protobuf
export OTEL_EXPORTER_OTLP_TRACES_ENDPOINT=http://127.0.0.1:6007/v1/traces
export OTEL_LOG_USER_PROMPTS=1 OTEL_LOG_TOOL_DETAILS=1 OTEL_LOG_TOOL_CONTENT=1
export OTEL_RESOURCE_ATTRIBUTES=openinference.project.name=claude-code
claude --strict-mcp-config --mcp-config .mcp.json "$@"
