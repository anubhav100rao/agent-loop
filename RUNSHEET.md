# Run sheet: X-ray the agent you already use (15 min)

## Before the session (10 min, once)

```bash
cd xray-demo && source .venv/bin/activate
set -a; . ../.env; set +a; export OPENAI_API_KEY=$OPEN_AI_API_KEY  # nano_agent.py only
scripts/reset.sh && scripts/check.sh  # must print READY
```

Screen: terminal on the left, browser on the right, both at large font
(terminal 20pt+, browser zoom 150%).

Run all commands from a normal terminal (Terminal.app / iTerm), not from
a shell inside the Claude desktop app: that shell's environment breaks
the `claude` login.

Backups already exist from a clean headless run (8 requests, 26 s):
`backup/trace.html` (full trace, open in a browser) and
`backup/run.typescript` (terminal output, `cat` it). If the network dies
on stage, use those. To re-record:

```bash
script -q backup/run.typescript claude-tap -- --model sonnet --strict-mcp-config --mcp-config .mcp.json -p "<the task>"
claude-tap export <session id printed at exit> --format html -o backup/trace.html
scripts/reset.sh
```

Note: request #1 contains your account email and git name in a
`<system-reminder>` block. It will be on the projector.

## 0:00-1:00  Guess

Ask: "How many tokens does Claude Code send before it reads your first
word?" Take three guesses out loud. Write the highest on the board.

## 1:00-3:00  Run the task

```bash
claude-tap -- --model sonnet --strict-mcp-config --mcp-config .mcp.json
```

The dashboard opens at http://127.0.0.1:19527. Leave it; go back to the
terminal and type:

```
Ticket SHOP-142 says the checkout total is wrong. Read the ticket, find the cause,
fix it, make sure the tests pass, and leave a comment on the ticket.
```

Say: "This looks like any normal day at work." Approve a prompt if one
appears. When it finishes, show the proof:

```bash
cat mock_mcp/comments.json
```

## 3:00-5:00  Request #1

In the dashboard: click the newest row in **Conversation Log**, then the
**Trace** button (top left of the session page). In the left list set
ORDER to **Turn** and click the first turn whose **Tools** badge shows
about 34 tools (skip any earlier turn with no tools: housekeeping calls).

- Point at the counters under the buttons: **Input / Cache Read /
  Cache Create**. Their sum is the answer to the guess. In the dry
  runs it was about 52,000 tokens (2 input + 39,894 cache read + 12,203
  cache create), for a two-line prompt.
- Scroll the **System Prompt** panel top to bottom, slowly, without
  reading it.
- Scroll to the very bottom: the last message is the two lines you typed.

Point: most of the request is not your prompt.

## 5:00-7:00  Tools + MCP

Same turn. Click the **Tools** header to expand.

- Open **Bash**: a name, a description, a JSON schema.
- Scroll to **mcp__tracker__get_ticket**: a name, a description, a JSON
  schema. Show `mock_mcp/tracker_server.py` next to it: the docstring is
  the description, the type hints are the schema.

Point: an MCP tool is just another JSON schema in the list. About 31 built in,
3 ours.

## 7:00-9:00  Context growth

Click the next turn in the left list, then **Diff with Prev**. Repeat for
the turn after that.

- The diff only adds: one assistant message, one tool result.
- System prompt and all the tools are sent again every time.
- Read out the Input + Cache Read number on each turn as it climbs.

Point: every turn resends everything. This is where cost and context
limits come from. (Cache Read is why it is affordable.)

## 9:00-11:00  The loop

Click through the turns in order and read only the last message of each:

1. response: `tool_use` mcp__tracker__get_ticket (often with
   list_recent_deploys)
2. request: `tool_result` with the ticket JSON
3. response: `tool_use` Read `shop/cart.py` and `shop/test_cart.py`
4. Bash pytest (1 failed), Edit, Bash pytest (5 passed),
   mcp__tracker__add_comment
5. last turn: plain text, no `tool_use`. The loop ends.

This was the order in all three dry runs (8-9 requests, 26-32 s).

For one turn click **Request JSON** to show there is nothing else in it.

Point: the model never runs anything. It asks. The harness runs it.

## 11:00-14:00  Nano agent

Exit Claude Code (`/exit`), then:

```bash
scripts/reset.sh
wc -l nano_agent.py
```

Open `nano_agent.py`, scroll to `# The loop. This is the whole agent.`
Walk the three numbered comments: send everything, stop if no tool
calls, run tools and append results. Then:

```bash
python nano_agent.py --verbose "The tests in shop/ are failing. Find the bug and fix it."
python -m pytest shop -q
```

Expect about 7 requests in 10 s. Point at `sending N messages` growing each request: same context
growth, same loop, 89 lines. It runs on an OpenAI model: the loop does
not care whose model is underneath.

## 14:00-15:00  Close

"You use this daily. This course is about knowing why it works and when
it won't." Tease: later we put several of these loops on one incident
and watch them coordinate. Hand back to the founders.

## If something goes wrong

| Problem | Do this |
|---|---|
| Claude Code asks to log in | `/login`, or switch to `backup/trace.html` |
| Tracker tools missing in Tools list | `scripts/check.sh`; restart the `claude-tap` command |
| Task wanders past 90 s | Esc, `scripts/reset.sh`, use the backup trace |
| nano agent errors on model ID | `MODEL=gpt-4.1-mini python nano_agent.py ...` |
| nano agent says 429 / no credits | add credits at platform.openai.com; walk the code only |
| Dashboard did not open | open http://127.0.0.1:19527 by hand |
