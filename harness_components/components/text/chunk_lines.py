"""Group supplied lines into consecutive non-overlapping batches."""
from ._shared import STRINGS, integer, array, check, spec
SPEC = spec("chunk_lines", "Group supplied strings into consecutive batches of at most size items.",
    {"lines": STRINGS, "size": integer(1)}, {"chunks": array(STRINGS)},
    {"lines": ["a", "b", "c"], "size": 2}, {"chunks": [["a", "b"], ["c"]]})
def run(payload):
    p = check(payload, SPEC)
    return {"chunks": [p["lines"][i:i + p["size"]] for i in range(0, len(p["lines"]), p["size"])]}
