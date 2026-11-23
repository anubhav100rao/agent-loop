# X-ray the coding agent you already use

**Audience** — Engineers who already use Claude Code or another coding agent.

**Takeaway** — An agent run is a loop of model requests and tool executions. A trace lets you see where that loop spent time and tokens, and how it recovered from failed calls.

| Time | What to cover | On screen |
|---|---|---|
| 0:00–2:00 | [Introduce the project](#introduce-the-project) | SHOP-142 or the terminal |
| 2:00–9:00 | [Observe Claude Code](#observe-claude-code) | Claude Code → `/context` → Phoenix |
| 9:00–14:00 | [Explain the agent loop](#explain-the-agent-loop) | `nano_agent.py` → loop diagram → terminal |
| 14:00–23:00 | [Trace and debug the loop](#trace-and-debug-the-loop) | Phoenix → clean run → run with injected timeouts |
| 23:00–25:00 | [Close](#close) | The two run summaries or the last trace |

Use the blockquotes as speaker notes. The commands and screen directions are your live cues.

## Introduce the project

**Say**

> Think about the last time you handed a ticket to a coding agent and got back “fixed, tests pass.” How would you tell what it tried before it got to that answer?
>
> I built X-ray to make that work visible. It’s a small demo with a buggy checkout, a local ticket tracker, and a 92-line Python agent that I wrote so we could read the whole loop. I set up both Claude Code and the Python agent to send traces to Phoenix, a trace viewer. We’ll start with Claude Code, walk through the Python loop, then make a tool fail and use the trace to see how the agent responds.

**Transition**

> Here’s the ticket. A customer expected to pay $88 after applying a coupon, and checkout charged $90. Let’s give Claude Code the ticket number and see what it does with it.

## Observe Claude Code

### Give it the ticket

Launch Claude Code with the demo’s tracker and telemetry enabled.

```bash
scripts/claude_phoenix.sh
```

Paste this prompt.

```text
Ticket SHOP-142 says the checkout total is wrong. Read the ticket, find the cause,
fix it, make sure the tests pass, and leave a comment on the ticket.
```

**While it runs**

> The prompt gives Claude Code a goal and a ticket ID. The ticket lives in our local mock tracker, which we connected through MCP, the Model Context Protocol. Watch for two tracker calls, one to look up the ticket and one to leave a comment. In between, Claude Code can read and edit files and run the tests.

**Show** the ticket lookup, a test run, the edit, and the final comment as they appear. Respond to the demo’s permission prompts if they appear. Expect one coupon test to fail before the fix and five tests to pass afterward. The exact call order can vary. From a separate terminal, show the saved comment to verify the write.

```bash
cat mock_mcp/comments.json
```

### Show the context

Type `/context` in Claude Code. Point at the system prompt, built-in tools, MCP tools, and conversation categories in the current session.

**Say**

> My task was two sentences. Look at what else is in the session. There are instructions for the agent, descriptions of the tools it can use, and messages from the work it just did. This view tells us what’s taking up context. To see which calls actually ran and how long they took, let’s open the trace.

Exit Claude Code with `/exit` and give the exporter a few seconds to flush.

### Open the Claude Code trace

In [Phoenix](http://127.0.0.1:6006), go to **Projects** → **claude-code** → **Traces**. Open the newest `claude code turn` for SHOP-142. A **span** is a timed record of a single operation. The trace groups the spans for the turn.

| Show | Say |
|---|---|
| The root `claude code turn` and the tree below it | “Here’s the prompt I just entered. Under it are the model requests and tool executions that made up this turn.” |
| `mcp__tracker__get_ticket` and `mcp__tracker__add_comment` | “These spans show the two tracker calls and their timing. The MCP payload fields are blank in this setup. We can verify the comment in the tracker file.” |
| A `Bash` span that ran pytest | “For this call, we can see the command, its result, and how long it took. That’s the tool running on this machine.” |
| The first and last task-model spans, if time allows | “The prompt token count tells us how much context each request carried. In the saved rehearsal, the main model went from roughly 27,500 to 33,200 input tokens. Those totals include cached input.” |

**Transition**

> Look at the pattern in the tree. There’s a model request, then some tool calls, and then another model request. What’s sending those tool results back to the model? That’s the part I wanted to make easy to read, so I wrote a tiny harness that does it in Python.

## Explain the agent loop

Open [`nano_agent.py`](nano_agent.py) at `# The loop. This is the whole agent.` Put the three numbered comments on screen. Use the same example through all three steps.

**Say**

> The harness is the code that runs the agent. It makes the model request, executes tools on the machine, and keeps the conversation history.
>
> First, it sends the system prompt, the task, and the tool schemas. A schema tells the model which tool it can ask for and what arguments to provide. On later requests this little agent also sends the history it has accumulated.
>
> Second, it reads the model’s reply. If there are no tool calls in the reply, the harness prints the answer and ends the run. A separate 20-turn limit keeps the demo bounded.
>
> Third, if the model asks for Bash with `python -m pytest shop -q`, the Python harness runs that command and appends the result to the conversation. On the next model request, the model can see which test failed and ask to read or edit the relevant file. That’s the pattern we just saw in Claude Code. This Python version has four tools.

If you have a minute, open the existing [interactive diagram](docs/agent_loop.html). Use the right arrow to advance to **The model replies with a tool call** → **The harness runs the tool** → **The result is appended to the context**. Point to the new result in the context strip.

```bash
open docs/agent_loop.html
```

**Run the small agent** on the same checkout bug. Reset first so the coupon test fails again.

```bash
scripts/reset.sh
FAULT= SESSION_ID=live-clean scripts/nano_phoenix.sh "The tests in shop/ are failing. Find the bug and fix it."
python -m pytest shop -q
```

**While it runs**

> Watch the line that says “sending N messages.” Every time the harness adds a tool request and its result, the next model call has more history. In a moment we can open one of those requests and see what was actually added.

When the independent pytest run shows `5 passed`, point to it and switch to Phoenix.

**Transition**

> We’ve seen the loop in code and watched it do the job. Now let’s use the trace to answer the question we started with. How did the agent get there?

## Trace and debug the loop

### Read the clean run

In Phoenix, go to **Projects** → **nano-agent** → **Traces**. Open the newest `agent run` for session `live-clean` and keep it open in one tab.

| Show | Say |
|---|---|
| The `agent run` root and its child spans | “The root ties the task to the final answer. Each `ChatCompletion` span is one model request. The spans named after tools are the harness executing those calls.” |
| The first and last `ChatCompletion` inputs | “The first request has the system message, the task and four tool schemas. In the last one you can see the tool calls and results that became part of the conversation.” |
| One `bash` span for pytest | “Here’s what the harness ran and what came back. We can check the tool result directly and see how much time the call took.” |

Point to the run’s token total and duration. If Phoenix shows a cost estimate, point to that too. Use the live numbers on screen.

### Run the same task with timeouts

**Say before running**

> Now I’ll reset the checkout again and give the agent the exact same prompt. This time the first two tool calls that try to run pytest will get an injected timeout response. Let’s see what happens to the run when the agent has to deal with that.

```bash
scripts/reset.sh
FAULT=timeout SESSION_ID=live-broken scripts/nano_phoenix.sh "The tests in shop/ are failing. Find the bug and fix it."
python -m pytest shop -q
```

**Stage cue** — Expect `[fault injected: timeout]`. The first two matching calls get a simulated error immediately. The message says “timed out after 60s” to imitate the tool failure. If the run takes too long or fails to fix the bug, switch to the saved comparison.

Once the tests pass, ask the room and pause for a beat.

> The agent says it fixed the bug, and the tests pass. Where would you look to see what those timeouts did to the run?

Open the newest `live-broken` trace in a second tab. Click a red `bash` span with the timeout in its output, then point to the model and tool calls that follow it. Compare total tokens and wall-clock duration with the clean run.

**Say while pointing to the spans**

> Here’s the timeout the harness returned. The next model request includes that result. Follow the calls after it and you can see what the agent tried to get the tests running again.

If the live comparison is unclear, open these saved rehearsal sessions. Both traces show a passing test run after the edit.

| Rehearsal run | Model requests | Total tokens | Duration | Tool spans marked as errors |
|---|---:|---:|---:|---:|
| `clean-1` | 5 | 7,860 | 12.9 s | 0 |
| `timeout-1` | 13 | 28,667 | 21.6 s | 4 |

**Say over the saved comparison**

> Both rehearsal runs ended with a fix. With the injected timeouts, model requests went from 5 to 13 and total tokens went from about 8,000 to about 29,000. Here’s the timeout and here are the extra calls that followed it. When an agent gets slower or more expensive, this gives me a place to start looking.

### If there’s time or someone asks

- **How is it wired?** Show [`tracing.py`](tracing.py). “The OpenAI SDK instrumentation records model requests. We wrap each Python tool call to record its inputs, outputs and errors. For Claude Code, the launcher enables its OpenTelemetry export and a local relay maps the spans into fields Phoenix displays.”
- **What if the tool returns the wrong thing?** Open saved session `stale-1`. “Here pytest kept returning an old failure. Phoenix recorded zero tool errors, and the agent went through about 48,000 tokens. A trace lets us inspect those results. An independent test or an assertion about the tool output helps us check correctness.”

## Close

Leave the clean and timeout run summaries visible. If you have only 30 seconds, read this as written.

> You already know what it feels like to give a task to a coding agent. Now you’ve seen what happens between the prompt and the answer. The model asks for tools, the harness runs them, and the results go back into the next request. When a run surprises you, open the trace and follow that sequence to the first call that behaved differently from what you expected. And when the agent says “fixed,” check the result as well as the path it took to get there.

## Before going live

Run the commands from the `xray-demo` repo. If the environment is already set up, start with the terminal tabs.

```bash
uv venv .venv && uv pip install --python .venv/bin/python -r requirements.txt
test -e .env || cp .env.example .env
```

Set `OPENROUTER_API_KEY` in the local `.env` if needed. Use a regular terminal and open `claude` once beforehand to handle login and the workspace trust prompt. The traced launcher expects Claude Code 2.1.139 or later.

| Where | Prepare |
|---|---|
| Terminal 1 | Run `scripts/phoenix.sh` and leave it running. Start early if Phoenix needs to download. |
| Terminal 2 | Run `source .venv/bin/activate`, then `scripts/reset.sh && scripts/check.sh`. Expect one planted test failure, four passes, three tracker tools, and `READY`. Check for any `WARN` lines. |
| Terminal 3 | Keep it at the repo root for checking the tracker comment and running commands separately. |
| Browser | Open [Phoenix](http://127.0.0.1:6006). Keep the saved Claude Code trace (`872b223c`, 19:02 IST) and the `clean-1` and `timeout-1` sessions handy. |
| Editor | Open `nano_agent.py` at the loop and keep `tracing.py` nearby for questions. |

`scripts/reset.sh` restores the tracked files under `shop/` and clears the demo’s ticket comments. Run it after rehearsing so the presentation starts with the bug in place.

**If you have 15 minutes** — Use 1 minute for the intro, 4 for Claude Code and its trace, 3 for the Python loop, 6 for the clean and timeout traces, and 1 to close. Show one context category, one Claude tool span, and one timeout span. Use the saved nano-agent traces to keep the timing predictable.

| If this happens | Do this |
|---|---|
| Claude Code asks to log in or the live task runs past 90 seconds | Use the saved Claude Code trace and narrate the ticket. In the live terminal use Esc to interrupt a long-running task. |
| Claude Code trace is missing | Wait a few seconds after `/exit`, refresh the project, and check the time range. Use the saved trace if the new one stays missing. |
| Nano-agent hits an API error or takes too long | Stop the run if needed and open `clean-1` and `timeout-1`. Use the exact numbers in the rehearsal table. |
| Network or Phoenix is unavailable | Show the Python loop and the local diagram. Walk through the saved comparison using the numbers above. Local Phoenix can serve saved traces from `.phoenix/` when it is running. |
