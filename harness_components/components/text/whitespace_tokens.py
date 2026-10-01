"""Locate runs of non-whitespace code points."""
import re
from ._shared import STRING, INTEGER, array, obj, check, spec
SPEC = spec("whitespace_tokens", "Split only on Unicode whitespace, preserving punctuation and exact code-point spans.",
    {"text": STRING}, {"tokens": array(obj({"text": STRING, "start": INTEGER, "end": INTEGER}))},
    {"text": " a,b\t🙂 "}, {"tokens": [{"text": "a,b", "start": 1, "end": 4}, {"text": "🙂", "start": 5, "end": 6}]})
def run(payload):
    return {"tokens": [{"text": match.group(), "start": match.start(), "end": match.end()} for match in re.finditer(r"\S+", check(payload, SPEC)["text"])]}
