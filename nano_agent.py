"""nano_agent.py: a coding agent in one loop.  Usage: python nano_agent.py [--verbose] "task" """
import os
import subprocess
import sys

import anthropic

MODEL = os.environ.get("MODEL", "claude-opus-5-5")
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
    return {"name": name, "description": description,
            "input_schema": {"type": "object", "required": list(params),
                             "properties": {p: {"type": "string"} for p in params}}}


TOOLS = [
    schema("read_file", "Read a file and return its contents.", "path"),
    schema("write_file", "Create or overwrite a file.", "path", "content"),
    schema("edit_file", "Replace one exact string in a file. `old` must appear once.", "path", "old", "new"),
    schema("bash", "Run a shell command and return its output.", "command"),
]


def main():
    task = " ".join(arg for arg in sys.argv[1:] if arg != "--verbose")
    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY
    messages = [{"role": "user", "content": task}]

    # The loop. This is the whole agent.
    for turn in range(1, 21):
        if VERBOSE:
            print(f"\n--- request {turn}: sending {len(messages)} messages ---")

        # 1. Send everything so far: system prompt, tool schemas, full history.
        response = client.messages.create(
            model=MODEL, max_tokens=4096, system=SYSTEM, tools=TOOLS, messages=messages)
        messages.append({"role": "assistant", "content": response.content})

        # 2. No tool calls means the model is done: print the answer and stop.
        calls = [block for block in response.content if block.type == "tool_use"]
        if not calls:
            print("\n" + "".join(b.text for b in response.content if b.type == "text"))
            return

        # 3. The model only asked. We run each tool and send the results back.
        results = []
        for call in calls:
            if VERBOSE:
                print(f"  tool call: {call.name}({str(call.input)[:100]})")
            try:
                output = FUNCTIONS[call.name](**call.input)
            except Exception as error:
                output = f"error: {error}"
            results.append({"type": "tool_result", "tool_use_id": call.id, "content": output})
        messages.append({"role": "user", "content": results})

    print("stopped: hit the 20 turn limit")


if __name__ == "__main__":
    main()
