"""Truncate to a code-point budget including an optional marker."""
from ._shared import STRING, BOOLEAN, integer, check, spec
SPEC = spec("truncate_codepoints", "Truncate to at most limit code points including marker; may split grapheme clusters.",
    {"text": STRING, "limit": integer(), "marker": STRING}, {"text": STRING, "truncated": BOOLEAN},
    {"text": "abcdef", "limit": 5, "marker": "…"}, {"text": "abcd…", "truncated": True}, optional=("marker",))
def run(payload):
    p = check(payload, SPEC)
    if len(p["text"]) <= p["limit"]:
        return {"text": p["text"], "truncated": False}
    marker = p.get("marker", "")[:p["limit"]]
    return {"text": p["text"][:p["limit"] - len(marker)] + marker, "truncated": True}
