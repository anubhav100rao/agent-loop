"""faults.py: break nano_agent.py's tools on purpose, so there is something to debug.

FAULT=timeout  the first 2 pytest runs fail with a fake timeout. The agent should
               retry and recover: red TOOL spans, extra LLM turns, same result.
FAULT=stale    pytest always returns the output of the first run (the failure), as
               if a cache were stuck. The agent keeps "fixing" working code: a
               runaway loop you can only explain by reading the TOOL span output.
"""
import os


def inject(agent):
    fault = os.environ.get("FAULT")
    if not fault:
        return
    real_bash = agent["FUNCTIONS"]["bash"]
    state = {"pytest_runs": 0, "first_output": None}

    def bash(command):
        if "pytest" not in command:
            return real_bash(command)
        state["pytest_runs"] += 1
        if fault == "timeout" and state["pytest_runs"] <= 2:
            return "error: command timed out after 60s"
        output = real_bash(command)
        if fault == "stale":
            state["first_output"] = state["first_output"] or output
            return state["first_output"]
        return output

    agent["FUNCTIONS"]["bash"] = bash
    print(f"[fault injected: {fault}]")
