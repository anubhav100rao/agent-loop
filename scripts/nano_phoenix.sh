#!/bin/sh
# Run nano_agent.py on OpenRouter with Phoenix tracing.
# usage: scripts/nano_phoenix.sh "task"              clean run
#        FAULT=timeout scripts/nano_phoenix.sh "..."  flaky tool, agent recovers
#        FAULT=stale   scripts/nano_phoenix.sh "..."  lying tool, runaway loop
# Reads OPENROUTER_API_KEY from .env. Start scripts/phoenix.sh first, in another tab.
cd "$(dirname "$0")/.." || exit 1
[ -f .env ] && { set -a; . ./.env; set +a; }   # OPENROUTER_API_KEY, MODEL
[ -n "$OPENROUTER_API_KEY" ] || { echo "OPENROUTER_API_KEY missing: copy .env.example to .env"; exit 1; }
curl -s -o /dev/null http://127.0.0.1:6006 || { echo "Phoenix not running: scripts/phoenix.sh"; exit 1; }
PHOENIX=1 OPENAI_BASE_URL=https://openrouter.ai/api/v1 OPENAI_API_KEY=$OPENROUTER_API_KEY \
  MODEL=${MODEL:-openai/gpt-6.2-sol} PHOENIX_PROJECT=${PHOENIX_PROJECT:-nano-agent} \
  exec .venv/bin/python nano_agent.py --verbose "$@"
