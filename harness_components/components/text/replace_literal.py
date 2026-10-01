"""Replace literal non-overlapping occurrences, with literal replacement."""
from ._shared import STRING, INTEGER, integer, check, nonempty, spec
SPEC = spec("replace_literal", "Replace non-overlapping exact literals; count limits replacements and replacement backslashes have no special meaning.",
    {"text": STRING, "old": STRING, "new": STRING, "count": integer()}, {"text": STRING, "replaced": INTEGER},
    {"text": "a.a", "old": ".", "new": "-"}, {"text": "a-a", "replaced": 1}, optional=("count",))
def run(payload):
    p = check(payload, SPEC)
    old = nonempty(p["old"], "old")
    count = p.get("count", p["text"].count(old))
    return {"text": p["text"].replace(old, p["new"], count), "replaced": min(count, p["text"].count(old))}
