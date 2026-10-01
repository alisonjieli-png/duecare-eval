"""Expand a normalized prefix against a supplied lexicon; return sorted unique normalized terms, including all terms for an empty prefix."""
from . import _common as C

SPEC = C.spec("expand_prefix", "Expand a normalized prefix against a supplied lexicon; return sorted unique normalized terms, including all terms for an empty prefix.",
    {'lexicon': C.STRINGS, 'prefix': C.S}, {'terms': C.STRINGS},
    {"lexicon": ["Café", "car", "CAT", "car"], "prefix": "CA"}, {"terms": ["café", "car", "cat"]}, sources=["unicode", "python"])


def run(payload: dict):
    p = C.check(payload, SPEC)
    prefix = C.normalized(p['prefix'])
    result = {'terms': sorted({C.normalized(term) for term in p['lexicon'] if C.normalized(term).startswith(prefix)})}
    return C.finish(result, SPEC)
