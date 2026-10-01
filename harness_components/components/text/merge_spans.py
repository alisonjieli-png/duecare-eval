"""Validate and union half-open code-point spans."""
from ._shared import SPANS, BOOLEAN, integer, check, valid_spans, merged_spans, spec
SPEC = spec("merge_spans", "Sort and merge overlapping half-open spans; optionally merge touching spans and always drop empty spans.",
    {"spans": SPANS, "text_length": integer(), "merge_touching": BOOLEAN}, {"spans": SPANS},
    {"spans": [[4, 6], [0, 3], [2, 5]], "text_length": 6}, {"spans": [[0, 6]]}, optional=("merge_touching",))
def run(payload):
    p = check(payload, SPEC)
    return {"spans": merged_spans(valid_spans(p["spans"], p["text_length"]), touching=p.get("merge_touching", True))}
