"""Stable Unicode code-point sort with an optional casefold key."""
from ._shared import STRING, STRINGS, BOOLEAN, check, spec
SPEC = spec("sort_lines", "Sort Unicode-split line bodies by code point or a casefolded key; locale-aware collation requires a separate operation.",
    {"text": STRING, "casefold": BOOLEAN, "reverse": BOOLEAN}, {"lines": STRINGS},
    {"text": "b\na\nA", "casefold": True}, {"lines": ["a", "A", "b"]}, optional=("casefold", "reverse"))
def run(payload):
    p = check(payload, SPEC)
    return {"lines": sorted(p["text"].splitlines(), key=str.casefold if p.get("casefold", False) else None, reverse=p.get("reverse", False))}
