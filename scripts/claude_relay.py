"""claude_relay.py: make Claude Code's OpenTelemetry traces readable in Phoenix.

Claude Code (OTLP/HTTP) -> this relay on :6007 -> Phoenix on :6006

Claude Code names every tool span "claude_code.tool", keeps tool input/output in
a span event and uses its own token attribute names, so Phoenix shows empty
columns and $0 cost. This relay buffers each trace until its root span arrives,
then rewrites it into OpenInference conventions:

  claude_code.interaction  -> AGENT span "claude code turn", input = your prompt
  claude_code.llm_request  -> LLM span named after the model, token counts set
  claude_code.tool         -> TOOL span named after the tool, input/output filled
  tool.execution, tool.blocked_on_user -> folded into the tool span

It also drops your email and account IDs. usage: python scripts/claude_relay.py
"""
import gzip
import json
import os
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import ExportTraceServiceRequest
from opentelemetry.proto.trace.v1.trace_pb2 import ResourceSpans, ScopeSpans, Status

PHOENIX = "http://127.0.0.1:6006/v1/traces"
PRIVATE = {"user.email", "user.id", "user.account_id", "user.account_uuid", "organization.id"}
OUTPUT_KEYS = ("output", "content", "diff", "result")
FLUSH_AFTER = 120  # seconds: send a trace even if its root never arrives
HERE = os.getcwd() + "/"  # shown paths become relative to the repo

lock = threading.Lock()
pending = {}  # trace_id -> {"spans": [(resource, scope, span)], "seen": time}


def attrs(item):
    return {kv.key: kv.value for kv in item.attributes}


def text(value):
    for field in ("string_value", "int_value", "double_value", "bool_value"):
        if value.HasField(field):
            return str(getattr(value, field))
    return ""


def put(span, key, value):
    for kv in span.attributes:
        if kv.key == key:
            span.attributes.remove(kv)
            break
    kv = span.attributes.add(key=key)
    if isinstance(value, int):
        kv.value.int_value = value
    else:
        kv.value.string_value = str(value)


def drop(item, *keys):
    for kv in [kv for kv in item.attributes if kv.key in keys]:
        item.attributes.remove(kv)


def scrub(item):
    drop(item, *PRIVATE)


def rewrite(entries):
    """Turn one complete Claude Code trace into OpenInference spans."""
    by_id = {e[2].span_id: e[2] for e in entries}
    keep = []
    for resource, scope, span in entries:
        a = {k: text(v) for k, v in attrs(span).items()}
        kind = a.get("span.type", "")
        if kind in ("tool.execution", "tool.blocked_on_user"):
            parent = by_id.get(span.parent_span_id)
            if parent is not None and kind == "tool.execution" and a.get("success", "").lower() == "false":
                parent.status.code = Status.STATUS_CODE_ERROR
            for child in by_id.values():  # reparent anything under the dropped span
                if child.parent_span_id == span.span_id:
                    child.parent_span_id = span.parent_span_id
            continue
        if kind == "interaction":
            span.name = "claude code turn"
            put(span, "openinference.span.kind", "AGENT")
            put(span, "input.value", a.get("user_prompt", ""))
        elif kind == "llm_request":
            model = a.get("llm.model_name", a.get("model", "llm")).split("[")[0]
            span.name = model
            put(span, "openinference.span.kind", "LLM")
            put(span, "llm.model_name", model)
            fresh, read, write = (int(a.get(k, 0) or 0) for k in
                                  ("input_tokens", "cache_read_tokens", "cache_creation_tokens"))
            out = int(a.get("output_tokens", 0) or 0)
            put(span, "llm.token_count.prompt", fresh + read + write)
            put(span, "llm.token_count.prompt_details.cache_read", read)
            put(span, "llm.token_count.prompt_details.cache_write", write)
            put(span, "llm.token_count.completion", out)
            put(span, "llm.token_count.total", fresh + read + write + out)
            # Only a request id, not the reply. Phoenix rebuilds output from gen_ai.response.id.
            drop(span, "output.value", "output.mime_type", "gen_ai.response.id")
        elif kind == "tool":
            span.name = a.get("tool_name", "tool")
            put(span, "openinference.span.kind", "TOOL")
            put(span, "tool.name", span.name)
            for event in span.events:
                if event.name != "tool.output":
                    continue
                ev = {k: text(v).replace(HERE, "") for k, v in attrs(event).items()}
                outputs = [ev.pop(k) for k in OUTPUT_KEYS if k in ev]
                if ev:
                    put(span, "input.value", json.dumps(ev))
                    put(span, "input.mime_type", "application/json")
                if outputs:
                    put(span, "output.value", "\n".join(outputs))
        scrub(span)
        keep.append((resource, scope, span))
    return keep


def send(entries):
    request = ExportTraceServiceRequest()
    for resource, scope, span in entries:
        rs = request.resource_spans.add()
        rs.resource.CopyFrom(resource)
        scrub(rs.resource)
        ss = rs.scope_spans.add()
        ss.scope.CopyFrom(scope)
        ss.spans.add().CopyFrom(span)
    body = request.SerializeToString()
    req = urllib.request.Request(PHOENIX, data=body, headers={"Content-Type": "application/x-protobuf"})
    urllib.request.urlopen(req, timeout=10).read()


def flush(trace_id):
    with lock:
        entry = pending.pop(trace_id, None)
    if entry:
        spans = rewrite(entry["spans"])
        send(spans)
        print(f"relay: sent trace {trace_id.hex()[:8]} ({len(spans)} spans)", flush=True)


def sweeper():
    while True:
        time.sleep(10)
        with lock:
            stale = [t for t, e in pending.items() if time.time() - e["seen"] > FLUSH_AFTER]
        for trace_id in stale:
            flush(trace_id)


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        if self.headers.get("Content-Encoding") == "gzip":
            body = gzip.decompress(body)
        request = ExportTraceServiceRequest()
        request.ParseFromString(body)
        complete = []
        with lock:
            for rs in request.resource_spans:
                for ss in rs.scope_spans:
                    for span in ss.spans:
                        entry = pending.setdefault(span.trace_id, {"spans": [], "seen": 0})
                        entry["spans"].append((rs.resource, ss.scope, span))
                        entry["seen"] = time.time()
                        if not span.parent_span_id:
                            complete.append(span.trace_id)
        for trace_id in complete:
            flush(trace_id)
        self.send_response(200)
        self.send_header("Content-Type", "application/x-protobuf")
        self.end_headers()
        self.wfile.write(b"")

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    threading.Thread(target=sweeper, daemon=True).start()
    print("relay: listening on http://127.0.0.1:6007 -> Phoenix", flush=True)
    ThreadingHTTPServer(("127.0.0.1", 6007), Handler).serve_forever()
