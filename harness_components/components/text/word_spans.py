"""Locate Python-regex word runs without linguistic claims."""
import re
from ._shared import STRING, INTEGER, array, obj, check, spec, REGEX_SOURCE
SPEC = spec("word_spans", "Locate Unicode alphanumeric/underscore runs using Python regex word characters; combining marks and apostrophes split runs.",
    {"text": STRING}, {"tokens": array(obj({"text": STRING, "start": INTEGER, "end": INTEGER}))},
    {"text": "a_1, b"}, {"tokens": [{"text": "a_1", "start": 0, "end": 3}, {"text": "b", "start": 5, "end": 6}]}, sources=(REGEX_SOURCE,))
def run(payload):
    return {"tokens": [{"text": match.group(), "start": match.start(), "end": match.end()} for match in re.finditer(r"\w+", check(payload, SPEC)["text"])]}
