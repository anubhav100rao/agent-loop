# xray-demo

X-ray the agent you already use: trace what Claude Code sends to the
model, then run the same loop in 89 lines (`nano_agent.py`).

## Setup

```bash
uv venv .venv && uv pip install --python .venv/bin/python -r requirements.txt
source .venv/bin/activate
set -a; . ../.env; set +a; export OPENAI_API_KEY=$OPEN_AI_API_KEY   # only nano_agent.py needs this
claude                         # once: accept the trust dialog, /login if asked
# use a normal terminal, not a shell inside the Claude desktop app
scripts/check.sh               # must end with READY
```

## Phoenix tracing (span view of the loop)

```bash
scripts/phoenix.sh                     # tab 1: UI at http://127.0.0.1:6006, data in .phoenix/
scripts/nano_phoenix.sh "The tests in shop/ are failing. Find the bug and fix it."
FAULT=timeout scripts/nano_phoenix.sh "..."   # first 2 pytest runs fail, agent recovers
```

Runs on OpenRouter (`OPENROUTER_API_KEY`, model `openai/gpt-6.2-sol`).
`tracing.py` adds the spans; `nano_agent.py` only gets a 3-line hook.

## Run

See `RUNSHEET.md`. Between runs: `scripts/reset.sh`.
