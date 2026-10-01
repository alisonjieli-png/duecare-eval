"""Measure strict UTF-8 encoding length."""
from ._shared import STRING, INTEGER, check, spec
SPEC = spec("utf8_length", "Count UTF-8 bytes using strict encoding; lone Unicode surrogates raise ValueError.",
    {"text": STRING}, {"bytes": INTEGER}, {"text": "é🙂"}, {"bytes": 6})
def run(payload):
    text = check(payload, SPEC)["text"]
    try:
        return {"bytes": len(text.encode("utf-8"))}
    except UnicodeEncodeError as exc:
        raise ValueError("text contains an unpaired surrogate") from exc
