"""Replace specified regions with a constant marker."""
from ._shared import STRING, SPANS, check, valid_spans, merged_spans, spec
SPEC = spec("redact_spans", "Replace each unioned nonempty span with a marker; only supplied spans are redacted, with no automatic PII detection.",
    {"text": STRING, "spans": SPANS, "marker": STRING}, {"text": STRING, "spans": SPANS},
    {"text": "abc def", "spans": [[0, 3]]}, {"text": "[REDACTED] def", "spans": [[0, 3]]}, optional=("marker",))
def run(payload):
    p = check(payload, SPEC)
    spans = merged_spans(valid_spans(p["spans"], len(p["text"])))
    result, end = [], 0
    for start, stop in spans:
        result.extend((p["text"][end:start], p.get("marker", "[REDACTED]")))
        end = stop
    result.append(p["text"][end:])
    return {"text": "".join(result), "spans": spans}
