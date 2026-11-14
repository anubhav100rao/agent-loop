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

## Run

See `RUNSHEET.md`. Between runs: `scripts/reset.sh`.
