"""Require all normalized query tokens; an empty required set is satisfied and missing tokens remain explicit."""
from . import _common as C

SPEC = C.spec("match_all_tokens", "Require all normalized query tokens; an empty required set is satisfied and missing tokens remain explicit.",
    {'text': C.S, 'terms': C.STRINGS}, {'matched': C.B, 'missing_terms': C.STRINGS},
    {"text": "Blue red.", "terms": ["blue", "GREEN"]}, {"matched": False, "missing_terms": ["green"]}, sources=["regex", "unicode"])


def run(payload: dict):
    p = C.check(payload, SPEC)
    available = set(C.terms(p['text']))
    wanted = {word for term in p['terms'] for word in C.terms(term)}
    missing = sorted(wanted - available)
    result = {'matched': not missing, 'missing_terms': missing}
    return C.finish(result, SPEC)
