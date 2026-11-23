# Demo guide: agent loops and tool-call observability

One talk, three acts, about 25 minutes:

1. **X-ray** (claude-tap): what Claude Code actually sends to the model.
2. **The loop** (`nano_agent.py`): the same loop in 92 lines.
3. **Observability** (Phoenix): the loop drawn as a span tree, then broken on purpose.

Takeaway line: *"You use this daily. This course is about knowing why it works and when it won't."*

`RUNSHEET.md` has the same flow with more click-by-click detail. This file is
the overview: what to run, what to show, what to expect.

---

## 0. Prepare (30 min before)

### One-time setup

```bash
cd xray-demo
uv venv .venv && uv pip install --python .venv/bin/python -r requirements.txt
```

Add the keys to `../.env` (one level above the repo, never committed):

```
OPEN_AI_API_KEY=...       # optional: plain nano_agent.py on OpenAI
OPENROUTER_API_KEY=...    # Phoenix act: model openai/gpt-6.2-sol
```

Run `claude` once in this folder to accept the trust dialog and log in.

### Three terminal tabs

Use Terminal.app or iTerm, **not** a shell inside the Claude desktop app
(its environment breaks the `claude` login). Font 20pt+.

**Tab 1: Phoenix server** (leave it running)

```bash
cd xray-demo && scripts/phoenix.sh
```

Expect `Phoenix is up and running` and the URL http://127.0.0.1:6006.
The first start downloads Phoenix through `uvx` (about 1 min), so do it early.

**Tab 2: the demo shell** (everything else runs here)

```bash
cd xray-demo && source .venv/bin/activate
set -a; . ../.env; set +a; export OPENAI_API_KEY=$OPEN_AI_API_KEY
scripts/reset.sh && scripts/check.sh
```

Expect every line to be `ok:` and the last line to be **`READY`**.
`WARN` lines are fine if you know which key you skipped.

**Tab 3: spare**, for `cat`, `git diff` and the fallback commands.

### Browser tabs (zoom 150%)

1. http://127.0.0.1:6006 → project **nano-agent** → **Traces**
2. http://127.0.0.1:19527 (claude-tap dashboard; it opens on its own in Act 1)
3. `backup/trace.html` and `backup/nano_trace.html` (offline copies)

### Editor

Open `nano_agent.py`, `tracing.py`, `mock_mcp/tracker_server.py` and `shop/cart.py`.

---

## Act 1: X-ray the agent you already use (10 min)

### 1.1 The guess (1 min)

Ask the room: **"How many tokens does Claude Code send before it reads your
first word?"** Take three guesses and write down the highest.

### 1.2 Run a normal task (2 min)

```bash
claude-tap -- --model sonnet --strict-mcp-config --mcp-config .mcp.json
```

The dashboard opens at http://127.0.0.1:19527. In Claude Code, type:

```
Ticket SHOP-142 says the checkout total is wrong. Read the ticket, find the cause,
fix it, make sure the tests pass, and leave a comment on the ticket.
```

**Expect** (about 30 s, 8-9 requests): `get_ticket` on the tracker MCP →
read `cart.py` and the tests → pytest (1 failed) → edit → pytest (5 passed) →
`add_comment`. Then show the proof:

```bash
cat mock_mcp/comments.json
```

Say: *"Looks like a normal day at work."*

### 1.3 Request #1 (2 min)

Dashboard: newest row → **Trace** → ORDER **Turn** → the first turn with about
**34 tools**.

- **Input + Cache Read + Cache Create**: about **52,000 tokens**. Answer the guess.
- Scroll the **System Prompt** slowly, without reading it out.
- The last message is your two lines.

> **Privacy:** request #1 includes your account email in a `<system-reminder>`.
> It will be on the projector.

**Point:** most of the request is not your prompt.

### 1.4 Tools and MCP (2 min)

Same turn → expand **Tools** → open **Bash**, then **mcp__tracker__get_ticket**.
Put `mock_mcp/tracker_server.py` next to it: the docstring is the description
and the type hints are the schema.

**Point:** an MCP tool is just another JSON schema in the list.

### 1.5 Context growth and the loop (3 min)

Next turn → **Diff with Prev**, twice. Only one assistant message and one
tool result are added; everything else is sent again. Read the token count
as it climbs. Then click through the turns, reading only the last message:
`tool_use` → `tool_result` → ... → plain text (the loop ends).

**Point:** the model never runs anything. It asks, and the harness runs it.

Exit Claude Code with `/exit`.

---

## Act 2: The whole loop in 92 lines (4 min)

```bash
scripts/reset.sh
wc -l nano_agent.py
```

In the editor, scroll to `# The loop. This is the whole agent.` and walk the
three numbered comments:

1. send everything (system prompt, tools, history)
2. no tool calls → print the answer and stop
3. run each tool and append the result

Run it through the same tracer:

```bash
scripts/nano_traced.sh "The tests in shop/ are failing. Find the bug and fix it."
python -m pytest shop -q
```

**Expect:** about 7 requests in 10 s, `sending N messages` growing, then
`5 passed`. In the claude-tap dashboard, put its Turn 1 next to Claude Code's:
**4 tools instead of about 34, about 250 tokens instead of about 52,000**, same shape.

**Point:** same loop. The model underneath doesn't matter.

---

## Act 3: Observability with Phoenix (10 min)

Bridge: *"claude-tap shows what the **model** receives. It can't see what
the **harness** does between requests: how long the tools took, which ones
failed. For that you need traces."*

### 3.1 Clean run (3 min)

```bash
scripts/reset.sh
SESSION_ID=live-clean scripts/nano_phoenix.sh "The tests in shop/ are failing. Find the bug and fix it."
```

**Expect** in the terminal: about 5 requests, 13-30 s, a "Fixed `Cart.total()`..."
message, then `trace: http://127.0.0.1:6006`.

In Phoenix: refresh **Traces** → click the newest **agent run**.

| Click | Show | Say |
|---|---|---|
| Left tree | ChatCompletion → bash → read_file → ... | "The loop, drawn as a tree. LLM and tools take turns." |
| A `bash` span with pytest | Input = command, Output = test result, ~1 s | "The proxy never saw this." |
| The last ChatCompletion → Info | Full message list + 4 tool schemas | "Same content as claude-tap, attached to a step." |
| Top bar | Total Cost ~$0.01, Latency | "Every run has a price and a duration." |
| Root span | Input = task, Output = final answer | "One row per run, which you can search." |

### 3.2 Break it (4 min)

```bash
scripts/reset.sh
FAULT=timeout SESSION_ID=live-broken scripts/nano_phoenix.sh "The tests in shop/ are failing. Find the bug and fix it."
```

**Expect:** `[fault injected: timeout]`. The first two pytest runs return a fake
timeout. The agent detours (checks python, the venv, plugins) and still fixes
the bug in about 13 requests and about 30 s. The final message looks the same as the clean run.

Ask the room: **"Did anything go wrong?"** Then open the trace:

- **Red ✕** on `bash` spans → click one → `error: command timed out after 60s`.
- The detour: the extra ChatCompletion/bash pairs after it.
- Compare with the clean run (rehearsal numbers):

| | Clean | Broken |
|---|---|---|
| LLM calls | 5 | 13 |
| Tokens | 7.9k | 28.7k |
| Cost | 1× | ~3.6× |
| Failed tool spans | 0 | 4 |
| Final answer | fixed | fixed |

**Point:** the output was the same. Only the trace shows it cost 3.6× and
took a detour. For agents, "it worked" tells you little.

### 3.3 What a trace can't see (1 min, talk only)

Open session **stale-1** (a rehearsal trace already in Phoenix). There, pytest
kept returning the *old* failure, like a stuck cache. Result: **zero red spans**,
48k tokens, and the agent eventually ran `cat faults.py` and found the fault
injection itself.

**Point:** a tool that lies is not an error. Spans show symptoms. Catching
lies needs evals and assertions on tool outputs.

Do **not** run `FAULT=stale` live: it takes about 90 s and its path is unpredictable.

### 3.4 How it's wired (1 min)

Show `tracing.py`: `register(...)` plus `OpenAIInstrumentor` gives LLM spans for
free, and wrapping each tool function adds TOOL spans. `nano_agent.py` only got a
3-line hook. Everything is OpenTelemetry, so the same spans can go to
Phoenix, Langfuse, or any OTel backend.

### 3.5 Production slide (1 min)

- **Sampling**: you won't keep every trace.
- **PII redaction**: remember request #1 had an email in it.
- **Evals over traces**: grade outputs, not just status codes.
- **Sessions and cost dashboards**: per user, per feature.
- **Tools:** Phoenix (local, open source, as shown), Langfuse (self-host or
  cloud, prompt versions), and Claude Code's own OpenTelemetry export
  (`CLAUDE_CODE_ENABLE_TELEMETRY=1`).

---

## Close (1 min)

*"You use this daily. This course is about knowing why it works and when it
won't."* Tease: later sessions put several of these loops on one incident and
trace them together.

---

## Between rehearsals

```bash
scripts/reset.sh     # bug back, ticket comments cleared (< 1 s)
scripts/check.sh     # must print READY
```

## If something goes wrong

| Problem | Do this |
|---|---|
| `claude` asks to log in | `/login`, or open `backup/trace.html` |
| Tracker tools missing | `scripts/check.sh`, then restart the `claude-tap` command |
| Claude Code task runs past 90 s | Esc, `scripts/reset.sh`, use `backup/trace.html` |
| `Phoenix not running` | start `scripts/phoenix.sh` in tab 1 |
| New trace missing in Phoenix | refresh; time range (top right) = Last 7 Days |
| OpenRouter 401/402 | key expired or out of credit: show the rehearsal traces (clean-*, timeout-*, stale-1) |
| No network at all | `backup/trace.html`, `backup/nano_trace.html`, and the rehearsal traces in `.phoenix/` |
| Agent wanders on stage | Ctrl-C, `scripts/reset.sh`, show the rehearsal trace with the same name |

## File map

| File | Role |
|---|---|
| `shop/` | target app, one planted bug (coupon applied after tax) |
| `mock_mcp/tracker_server.py` | mock ticket tracker (MCP, stdio) |
| `nano_agent.py` | the agent loop |
| `tracing.py` | Phoenix/OpenTelemetry spans for the loop |
| `faults.py` | `FAULT=timeout` / `FAULT=stale` tool failures |
| `scripts/phoenix.sh` | Phoenix server (uvx, data in `.phoenix/`) |
| `scripts/nano_phoenix.sh` | traced agent run on OpenRouter |
| `scripts/nano_traced.sh` | agent run through claude-tap |
| `scripts/reset.sh`, `scripts/check.sh` | reset and preflight |
