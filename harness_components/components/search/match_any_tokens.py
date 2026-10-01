"""Test whether any normalized query tokens occur as complete Unicode word tokens; empty terms match nothing."""
from . import _common as C

SPEC = C.spec("match_any_tokens", "Test whether any normalized query tokens occur as complete Unicode word tokens; empty terms match nothing.",
    {'text': C.S, 'terms': C.STRINGS}, {'matched': C.B, 'matching_terms': C.STRINGS},
    {"text": "Blue red.", "terms": ["RED", "green"]}, {"matched": True, "matching_terms": ["red"]}, sources=["regex", "unicode"])


def run(payload: dict):
    p = C.check(payload, SPEC)
    available = set(C.terms(p['text']))
    wanted = {word for term in p['terms'] for word in C.terms(term)}
    matched = sorted(available & wanted)
    result = {'matched': bool(matched), 'matching_terms': matched}
    return C.finish(result, SPEC)
