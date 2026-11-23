"""tracing.py: send nano_agent.py's loop to Phoenix as a span tree.

    agent run (AGENT)
    ├── ChatCompletion (LLM)   <- automatic, from the OpenAI SDK instrumentation
    ├── bash (TOOL)            <- added here: what a request proxy never sees
    ├── ChatCompletion (LLM)
    └── ...

Turned on by PHOENIX=1 (see scripts/nano_phoenix.sh). nano_agent.py itself only
calls instrument(globals()) so the file on the projector stays a plain loop.
"""
import contextlib
import io
import json
import os
import sys
import uuid

from openinference.instrumentation.openai import OpenAIInstrumentor
from openinference.semconv.trace import OpenInferenceSpanKindValues, SpanAttributes
from opentelemetry.trace import Status, StatusCode
from phoenix.otel import register

KIND = SpanAttributes.OPENINFERENCE_SPAN_KIND


class Tee:
    """Write to the terminal and keep a copy, so the final answer lands on the root span."""
    def __init__(self, *streams):
        self.streams = streams

    def write(self, text):
        for stream in self.streams:
            stream.write(text)

    def flush(self):
        for stream in self.streams:
            stream.flush()


def instrument(agent):
    """Wrap the agent module's main() and each tool function in spans."""
    provider = register(project_name=os.environ.get("PHOENIX_PROJECT", "nano-agent"),
                        endpoint="http://127.0.0.1:6006/v1/traces", verbose=False)
    OpenAIInstrumentor().instrument(tracer_provider=provider)
    tracer = provider.get_tracer("nano_agent")
    session = os.environ.get("SESSION_ID", uuid.uuid4().hex[:8])

    def traced_tool(name, fn):
        def run(**args):
            with tracer.start_as_current_span(name) as span:
                span.set_attribute(KIND, OpenInferenceSpanKindValues.TOOL.value)
                span.set_attribute(SpanAttributes.TOOL_NAME, name)
                span.set_attribute(SpanAttributes.INPUT_VALUE, json.dumps(args))
                try:
                    output = fn(**args)
                except Exception as error:
                    span.record_exception(error)
                    span.set_status(Status(StatusCode.ERROR, str(error)))
                    raise
                span.set_attribute(SpanAttributes.OUTPUT_VALUE, output)
                if output.startswith("error"):
                    span.set_status(Status(StatusCode.ERROR, output[:200]))
                return output
        return run

    for name, fn in list(agent["FUNCTIONS"].items()):
        agent["FUNCTIONS"][name] = traced_tool(name, fn)

    main = agent["main"]

    def traced_main():
        task = " ".join(a for a in agent["sys"].argv[1:] if not a.startswith("--"))
        with tracer.start_as_current_span("agent run") as span:
            span.set_attribute(KIND, OpenInferenceSpanKindValues.AGENT.value)
            span.set_attribute(SpanAttributes.SESSION_ID, session)
            span.set_attribute(SpanAttributes.INPUT_VALUE, task)
            span.set_attribute("agent.model", agent["MODEL"])
            printed = io.StringIO()
            with contextlib.redirect_stdout(Tee(sys.stdout, printed)):
                main()
            answer = printed.getvalue().rsplit("---\n", 1)[-1]  # text after the last request
            answer = "\n".join(l for l in answer.splitlines() if not l.startswith("  tool call"))
            span.set_attribute(SpanAttributes.OUTPUT_VALUE, answer.strip())
            if "turn limit" in answer:
                span.set_status(Status(StatusCode.ERROR, "hit the turn limit"))
        provider.force_flush()
        print(f"\ntrace: http://127.0.0.1:6006  (project {os.environ.get('PHOENIX_PROJECT', 'nano-agent')})")

    agent["main"] = traced_main
