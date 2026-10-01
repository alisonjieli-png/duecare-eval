"""Find exact literal matches, optionally including overlaps."""
from ._shared import STRING, BOOLEAN, SPANS, check, literal_spans, spec
SPEC = spec("find_literal_spans", "Find exact literal code-point spans with optional overlaps; an empty needle is rejected.",
    {"text": STRING, "needle": STRING, "overlap": BOOLEAN}, {"spans": SPANS},
    {"text": "ababa", "needle": "aba", "overlap": True}, {"spans": [[0, 3], [2, 5]]}, optional=("overlap",))
def run(payload):
    p = check(payload, SPEC)
    return {"spans": literal_spans(p["text"], p["needle"], p.get("overlap", False))}
