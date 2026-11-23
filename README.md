# agent-loop

What happens inside the coding agent you already use: watch Claude Code fix
a ticket, run the same loop in 92 lines (`nano_agent.py`), then trace that
loop with Phoenix and break it on purpose.

## Setup

```bash
uv venv .venv && uv pip install --python .venv/bin/python -r requirements.txt
source .venv/bin/activate
cp .env.example .env            # then put your OPENROUTER_API_KEY in .env (git-ignored)
claude                         # once: accept the trust dialog, /login if asked
# use a normal terminal, not a shell inside the Claude desktop app
scripts/check.sh               # must end with READY
```

## Phoenix tracing (span view of the loop)

```bash
scripts/phoenix.sh                     # tab 1: UI at http://127.0.0.1:6006, data in .phoenix/
scripts/nano_phoenix.sh "The tests in shop/ are failing. Find the bug and fix it."
FAULT=timeout scripts/nano_phoenix.sh "..."   # first 2 pytest runs fail, agent recovers
scripts/claude_phoenix.sh              # Claude Code itself, traced (project claude-code)
```

Runs on OpenRouter; the scripts read `OPENROUTER_API_KEY` and `MODEL` from `.env`.
`tracing.py` adds the spans; `nano_agent.py` only gets a 3-line hook.

## Run

`demo.md` is the full presentation guide; `RUNSHEET.md` is the timed cue
card. Between runs: `scripts/reset.sh`.
