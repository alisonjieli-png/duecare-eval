"""Build consecutive n-grams without joining token contents."""
from ._shared import STRINGS, integer, array, check, spec
SPEC = spec("token_ngrams", "Return all overlapping consecutive token windows of size n.",
    {"tokens": STRINGS, "n": integer(1)}, {"ngrams": array(STRINGS)},
    {"tokens": ["a", "b", "c"], "n": 2}, {"ngrams": [["a", "b"], ["b", "c"]]})
def run(payload):
    p = check(payload, SPEC)
    return {"ngrams": [p["tokens"][i:i + p["n"]] for i in range(max(0, len(p["tokens"]) - p["n"] + 1))]}
