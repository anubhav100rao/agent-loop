# Demo guide: agent loops and tool-call observability

One talk, three acts, about 25 minutes:

1. **The agent you already use**: Claude Code fixes a ticket through an MCP
   tool, then `/context` shows what it carries before your first word.
2. **The loop**: `nano_agent.py`, the same loop in 92 lines.
3. **Observability**: Phoenix draws that loop as a span tree. Then we break
   a tool on purpose and find the problem from the trace.

Takeaway line: *"You use this daily. This course is about knowing why it works and when it won't."*

`RUNSHEET.md` is the timed cue card. This file has the details: what to run,
what to show, what to expect.

---

## 0. Prepare (30 min before)

### One-time setup

```bash
cd xray-demo
uv venv .venv && uv pip install --python .venv/bin/python -r requirements.txt
```

Add the key to `../.env` (one level above the repo, never committed):

```
OPENROUTER_API_KEY=...    # nano_agent.py via OpenRouter, model openai/gpt-6.2-sol
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
set -a; . ../.env; set +a
scripts/reset.sh && scripts/check.sh
```

Expect every line to be `ok:` and the last line to be **`READY`**.

**Tab 3: spare**, for `cat`, `git diff` and the fallback commands.

### Browser (zoom 150%)

http://127.0.0.1:6006 → project **nano-agent** → **Traces**.

### Editor

Open `nano_agent.py`, `tracing.py`, `mock_mcp/tracker_server.py` and `shop/cart.py`.

### Rehearse once

Do Act 1 once before the talk and write down the total that `/context`
shows. You'll compare it with the guesses on stage.

---

## Act 1: The agent you already use (8 min)

### 1.1 The guess (1 min)

Ask the room: **"How many tokens does Claude Code send before it reads your
first word?"** Take three guesses and write down the highest.

### 1.2 Run a normal task (2 min)

```bash
claude --strict-mcp-config --mcp-config .mcp.json
```

Type:

```
Ticket SHOP-142 says the checkout total is wrong. Read the ticket, find the cause,
fix it, make sure the tests pass, and leave a comment on the ticket.
```

**Expect** (about 30 s): `get_ticket` on the tracker MCP → read `cart.py` and
the tests → pytest (1 failed) → edit → pytest (5 passed) → `add_comment`.
Approve a prompt if one appears.

Say: *"Looks like a normal day at work."* Then in tab 3:

```bash
cat mock_mcp/comments.json
```

**Expect:** the comment Claude Code left on SHOP-142.

### 1.3 What it carries: `/context` (2 min)

In Claude Code, type `/context`.

**Expect:** a breakdown of the context window by category: system prompt,
system tools, **MCP tools**, messages, free space. Point at the totals:
most of it is system prompt and tool schemas, and only a small slice is
your messages. Compare with the guesses.

**Point:** most of each request is not your prompt, and all of it is sent
again on every turn.

### 1.4 An MCP tool is just a schema (2 min)

Point at the MCP tools line in `/context`, then show
`mock_mcp/tracker_server.py`: three functions. The docstring becomes the
tool description and the type hints become the JSON schema.

**Point:** an MCP tool is just another JSON schema in the list sent to the model.

Exit with `/exit`.

---

## Act 2: The whole loop in 92 lines (5 min)

```bash
scripts/reset.sh
wc -l nano_agent.py
```

In the editor, scroll to `# The loop. This is the whole agent.` and walk the
three numbered comments:

1. send everything (system prompt, tools, history)
2. no tool calls → print the answer and stop
3. run each tool and append the result

Run it, traced (this run becomes the trace for Act 3):

```bash
SESSION_ID=live-clean scripts/nano_phoenix.sh "The tests in shop/ are failing. Find the bug and fix it."
python -m pytest shop -q
```

**Expect:** about 5 requests in 13-30 s. `sending N messages` grows each
request (2 → 5 → 9 → 11 → 13). Tool calls appear as they happen: bash,
read_file, edit_file. Then a "Fixed `Cart.total()`..." message, then
`trace: http://127.0.0.1:6006`, then pytest prints `5 passed`.

**Point:** this is the same loop Claude Code runs, with 4 tools and a
one-line system prompt. The model never runs anything: it asks, and the
loop runs it.

---

## Act 3: Observability with Phoenix (10 min)

Bridge: *"The terminal shows what happened. It doesn't show what each step
cost, how long the tools took, or what exactly the model saw. Traces do."*

### 3.1 X-ray the clean run (4 min)

In Phoenix: refresh **Traces** → click the newest **agent run**.

| Click | Show | Say |
|---|---|---|
| Left tree | ChatCompletion → bash → read_file → ... | "The loop, drawn as a tree. LLM and tools take turns." |
| First ChatCompletion → Info | System prompt, the 4 tool schemas, the user message | "This is exactly what the model receives." |
| Last ChatCompletion | The full message history, every tool call and result | "Every turn resends everything." |
| Token counts, first to last ChatCompletion | about 231 → about 2.2k prompt tokens | "Context growth is where cost and limits come from." |
| A `bash` span running pytest | Input = command, Output = test result, ~1 s | "The harness runs the tool. The model only asked." |
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

### 3.4 How it's wired and the production slide (1 min)

Show `tracing.py`: `register(...)` plus `OpenAIInstrumentor` gives LLM spans for
free, and wrapping each tool function adds TOOL spans. `nano_agent.py` only got a
3-line hook. Everything is OpenTelemetry, so the same spans can go to Phoenix,
Langfuse, or any OTel backend.

In production, add:

- **Sampling**: you won't keep every trace.
- **PII redaction**: prompts and tool outputs contain user data.
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
| `claude` asks to log in | `/login`; if it fails, skip to Act 2 and describe Act 1 |
| Tracker tools missing in Claude Code | `scripts/check.sh`, then restart `claude` with the same flags |
| Claude Code task runs past 90 s | Esc, `scripts/reset.sh`, move on to `/context` anyway |
| `Phoenix not running` | start `scripts/phoenix.sh` in tab 1 |
| New trace missing in Phoenix | refresh; time range (top right) = Last 7 Days |
| OpenRouter 401/402 | key expired or out of credit: show the rehearsal traces (clean-*, timeout-*, stale-1) |
| No network at all | walk `nano_agent.py`, then show the rehearsal traces in `.phoenix/` |
| Agent wanders on stage | Ctrl-C, `scripts/reset.sh`, show the rehearsal trace with the same name |

## File map

| File | Role |
|---|---|
| `shop/` | target app, one planted bug (coupon applied after tax) |
| `mock_mcp/tracker_server.py` | mock ticket tracker (MCP, stdio) |
| `.mcp.json` | registers the tracker for Claude Code |
| `nano_agent.py` | the agent loop |
| `tracing.py` | Phoenix/OpenTelemetry spans for the loop |
| `faults.py` | `FAULT=timeout` / `FAULT=stale` tool failures |
| `scripts/phoenix.sh` | Phoenix server (uvx, data in `.phoenix/`) |
| `scripts/nano_phoenix.sh` | traced agent run on OpenRouter |
| `scripts/reset.sh`, `scripts/check.sh` | reset and preflight |
