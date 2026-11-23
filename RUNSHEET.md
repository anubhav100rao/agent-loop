# Run sheet: cue card (about 25 min)

Timed cues only. Commands, what to expect and fallbacks are in `demo.md`.

## Before (30 min)

```bash
scripts/phoenix.sh                                   # tab 1, leave running
cd xray-demo && source .venv/bin/activate            # tab 2
scripts/reset.sh && scripts/check.sh                 # must print READY
```

Browser: http://127.0.0.1:6006 → **nano-agent** → **Traces**. Terminal 20pt+, browser at 150% zoom.

## Act 1: the agent you already use (8 min)

| Time | Do | Point |
|---|---|---|
| 0:00 | Ask: "How many tokens does Claude Code send before it reads your first word?" Take 3 guesses | Set up the surprise |
| 1:00 | `claude --strict-mcp-config --mcp-config .mcp.json`, type the SHOP-142 task | A normal day at work |
| 3:00 | `cat mock_mcp/comments.json` | It really used our MCP tool |
| 3:30 | In Claude Code: `/context` | Most of the context is system prompt and tools, not your prompt |
| 5:00 | Show `mock_mcp/tracker_server.py` next to the `/context` MCP tools line | An MCP tool is just another JSON schema |
| 7:00 | `/exit` | |

## Act 2: the loop in 92 lines (5 min)

| Time | Do | Point |
|---|---|---|
| 8:00 | `scripts/reset.sh; wc -l nano_agent.py`, walk the 3 loop comments | Send everything → stop if no tool calls → run tools, append results |
| 10:00 | `scripts/nano_phoenix.sh "The tests in shop/ are failing. Find the bug and fix it."` | `sending N messages` grows: every turn resends everything |
| 12:00 | `python -m pytest shop -q` → 5 passed | Same loop as Claude Code. The model never runs anything |

## Act 3: observability with Phoenix (10 min)

| Time | Do | Point |
|---|---|---|
| 13:00 | Phoenix → newest **agent run** → the left tree | The loop drawn as a tree |
| 14:00 | First ChatCompletion → Info: system prompt, 4 tool schemas, message | This is exactly what the model receives |
| 15:00 | Last ChatCompletion: tokens 231 → ~2.2k across the turns | Context growth = cost and limits |
| 16:00 | A `bash` pytest span: command, output, ~1 s | The harness runs tools; the model only asks |
| 17:00 | `scripts/reset.sh; FAULT=timeout SESSION_ID=live-broken scripts/nano_phoenix.sh "..."` | Ask: "Did anything go wrong?" |
| 18:30 | Trace: red ✕ bash spans, the detour; 5 → 13 calls, 7.9k → 28.7k tokens, ~3.6× cost | Same answer, 3.6× cost. "It worked" tells you little |
| 20:30 | Session **stale-1** (rehearsal): zero red spans, 48k tokens, agent read `faults.py` | A tool that lies is not an error: you need evals |
| 21:30 | `tracing.py`: register + OpenAIInstrumentor + wrapped tools | It's all OpenTelemetry: Phoenix, Langfuse, any backend |
| 22:30 | Production slide: sampling, PII redaction, evals over traces, cost per user | |

## Close (1 min)

"You use this daily. This course is about knowing why it works and when it won't."
