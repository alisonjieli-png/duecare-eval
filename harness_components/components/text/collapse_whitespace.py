"""Collapse Unicode whitespace runs to one ASCII space."""
from ._shared import STRING, BOOLEAN, check, spec
SPEC = spec("collapse_whitespace", "Collapse Unicode whitespace; optionally preserve one space at each edge.",
    {"text": STRING, "trim": BOOLEAN}, {"text": STRING},
    {"text": " a\t b\n c "}, {"text": "a b c"}, optional=("trim",))
def run(payload):
    p = check(payload, SPEC)
    text = p["text"]
    collapsed = " ".join(text.split())
    if not p.get("trim", True) and text:
        if not collapsed:
            collapsed = " "
        else:
            collapsed = (" " if text[0].isspace() else "") + collapsed + (" " if text[-1].isspace() else "")
    return {"text": collapsed}
