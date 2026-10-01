"""Count supplied tokens, optionally using Unicode casefold."""
from collections import Counter
from ._shared import STRING, STRINGS, INTEGER, BOOLEAN, array, obj, check, spec
SPEC = spec("token_frequencies", "Count supplied tokens exactly or by casefolded value, sorted by descending count with first occurrence tie breaks.",
    {"tokens": STRINGS, "casefold": BOOLEAN}, {"tokens": array(obj({"token": STRING, "count": INTEGER}))},
    {"tokens": ["A", "a", "B"], "casefold": True}, {"tokens": [{"token": "a", "count": 2}, {"token": "b", "count": 1}]}, optional=("casefold",))
def run(payload):
    p = check(payload, SPEC)
    tokens = [token.casefold() for token in p["tokens"]] if p.get("casefold", False) else p["tokens"]
    return {"tokens": [{"token": token, "count": count} for token, count in Counter(tokens).most_common()]}
