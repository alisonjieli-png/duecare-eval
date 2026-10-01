"""Count characters without normalization or grapheme inference."""
from collections import Counter
from ._shared import STRING, INTEGER, array, obj, check, spec
SPEC = spec("character_frequencies", "Count exact Unicode code points in descending frequency, breaking ties by first occurrence.",
    {"text": STRING}, {"characters": array(obj({"character": STRING, "count": INTEGER}))},
    {"text": "aba "}, {"characters": [{"character": "a", "count": 2}, {"character": "b", "count": 1}, {"character": " ", "count": 1}]})
def run(payload):
    return {"characters": [{"character": char, "count": count} for char, count in Counter(check(payload, SPEC)["text"]).most_common()]}
