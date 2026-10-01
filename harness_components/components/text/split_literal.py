"""Split using a nonempty literal separator."""
from ._shared import STRING, STRINGS, integer, check, nonempty, spec
SPEC = spec("split_literal", "Split on a literal separator while retaining empty fields; optional maxsplit limits splits.",
    {"text": STRING, "separator": STRING, "maxsplit": integer()}, {"parts": STRINGS},
    {"text": "a::b::::", "separator": "::"}, {"parts": ["a", "b", "", ""]}, optional=("maxsplit",))
def run(payload):
    p = check(payload, SPEC)
    return {"parts": p["text"].split(nonempty(p["separator"], "separator"), p.get("maxsplit", -1))}
