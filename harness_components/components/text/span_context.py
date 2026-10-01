"""Extract bounded context around supplied spans."""
from ._shared import STRING, SPANS, INTEGER, integer, array, obj, check, valid_spans, spec
SPEC = spec("span_context", "Return exact matches with up to context code points before and after; offsets refer to the original text.",
    {"text": STRING, "spans": SPANS, "context": integer()},
    {"contexts": array(obj({"start": INTEGER, "end": INTEGER, "match": STRING, "before": STRING, "after": STRING, "context_start": INTEGER, "context_end": INTEGER}))},
    {"text": "abcdef", "spans": [[2, 4]], "context": 1},
    {"contexts": [{"start": 2, "end": 4, "match": "cd", "before": "b", "after": "e", "context_start": 1, "context_end": 5}]})
def run(payload):
    p = check(payload, SPEC)
    text, amount = p["text"], p["context"]
    result = []
    for start, end in valid_spans(p["spans"], len(text)):
        left, right = max(0, start - amount), min(len(text), end + amount)
        result.append({"start": start, "end": end, "match": text[start:end], "before": text[left:start], "after": text[end:right], "context_start": left, "context_end": right})
    return {"contexts": result}
