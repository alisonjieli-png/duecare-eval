"""Trim Unicode whitespace from the requested side."""
from ._shared import STRING, choice, check, spec
SPEC = spec("trim_whitespace", "Trim Python Unicode whitespace from either or both ends.",
    {"text": STRING, "side": choice("both", "left", "right")}, {"text": STRING},
    {"text": "  hello\n"}, {"text": "hello"}, optional=("side",))
def run(payload):
    p = check(payload, SPEC)
    method = {"both": str.strip, "left": str.lstrip, "right": str.rstrip}[p.get("side", "both")]
    return {"text": method(p["text"])}
