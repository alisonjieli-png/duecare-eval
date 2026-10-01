"""Extract the first pair of literal delimiters without nesting."""
from ._shared import STRING, BOOLEAN, INTEGER, check, nonempty, spec
SPEC = spec("extract_between", "Extract text after the first opening delimiter and before its next closing delimiter; nesting is not parsed.",
    {"text": STRING, "opening": STRING, "closing": STRING},
    {"found": BOOLEAN, "text": STRING, "start": INTEGER, "end": INTEGER},
    {"text": "a[bc]d", "opening": "[", "closing": "]"}, {"found": True, "text": "bc", "start": 2, "end": 4})
def run(payload):
    p = check(payload, SPEC)
    opening, closing = nonempty(p["opening"], "opening"), nonempty(p["closing"], "closing")
    start = p["text"].find(opening)
    end = p["text"].find(closing, start + len(opening)) if start >= 0 else -1
    if end < 0:
        return {"found": False, "text": "", "start": -1, "end": -1}
    start += len(opening)
    return {"found": True, "text": p["text"][start:end], "start": start, "end": end}
