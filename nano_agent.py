"""nano_agent.py: a coding agent in one loop.  Usage: python nano_agent.py [--verbose] "task" """
import json
import os
import subprocess
import sys

import openai

MODEL = os.environ.get("MODEL", "gpt-5.4-mini")
VERBOSE = "--verbose" in sys.argv
SYSTEM = "You are a coding agent working in the current directory. Use the tools to do the task."


def read_file(path):
    return open(path).read()


def write_file(path, content):
    open(path, "w").write(content)
    return f"wrote {path}"


def edit_file(path, old, new):
    text = open(path).read()
    if text.count(old) != 1:
        return f"error: `old` must appear exactly once in {path}, found {text.count(old)}"
    open(path, "w").write(text.replace(old, new))
    return f"edited {path}"


def bash(command):
    done = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=60)
    return (done.stdout + done.stderr)[-4000:] or "(no output)"


FUNCTIONS = {"read_file": read_file, "write_file": write_file, "edit_file": edit_file, "bash": bash}


def schema(name, description, *params):
    return {"type": "function", "function": {
        "name": name, "description": description,
        "parameters": {"type": "object", "required": list(params),
                       "properties": {p: {"type": "string"} for p in params}}}}


TOOLS = [
    schema("read_file", "Read a file and return its contents.", "path"),
    schema("write_file", "Create or overwrite a file.", "path", "content"),
    schema("edit_file", "Replace one exact string in a file. `old` must appear once.", "path", "old", "new"),
    schema("bash", "Run a shell command and return its output.", "command"),
]


def main():
    task = " ".join(arg for arg in sys.argv[1:] if arg != "--verbose")
    client = openai.OpenAI(timeout=30)  # reads OPENAI_API_KEY
    messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": task}]

    # The loop. This is the whole agent.
    for turn in range(1, 21):
        if VERBOSE:
            print(f"\n--- request {turn}: sending {len(messages)} messages ---")

        # 1. Send everything so far: system prompt, tool schemas, full history.
        response = client.chat.completions.create(model=MODEL, tools=TOOLS, messages=messages)
        reply = response.choices[0].message
        messages.append(reply)

        # 2. No tool calls means the model is done: print the answer and stop.
        if not reply.tool_calls:
            print("\n" + (reply.content or "(no text)"))
            return

        # 3. The model only asked. We run each tool and send the results back.
        for call in reply.tool_calls:
            name, args = call.function.name, json.loads(call.function.arguments)
            if VERBOSE:
                print(f"  tool call: {name}({str(args)[:100]})")
            try:
                output = FUNCTIONS[name](**args)
            except Exception as error:
                output = f"error: {error}"
            messages.append({"role": "tool", "tool_call_id": call.id, "content": output})

    print("stopped: hit the 20 turn limit")


if __name__ == "__main__":
    if os.environ.get("PHOENIX"):  # optional: trace the loop (tracing.py, faults.py)
        import faults, tracing
        faults.inject(globals()); tracing.instrument(globals())
    main()
