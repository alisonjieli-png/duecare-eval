"""Build an FTS5 NEAR group from at least two literal phrases and a nonnegative token-gap allowance; the query remains data rather than executable SQL."""
from . import _common as C

SPEC = C.spec("fts5_near_query", "Build an FTS5 NEAR group from at least two literal phrases and a nonnegative token-gap allowance; the query remains data rather than executable SQL.",
    {'phrases': C.arr(C.S, 2), 'distance': C.I}, {'query': C.S},
    {"phrases": ["red", "blue"], "distance": 2}, {"query": "NEAR(\"red\" \"blue\", 2)"}, sources=["fts5"])


def run(payload: dict):
    p = C.check(payload, SPEC)
    C.require(all(any(char.isalnum() for char in phrase) for phrase in p['phrases']), 'each phrase needs alphanumeric content')
    result = {'query': 'NEAR(' + ' '.join(C.fts_quote(phrase) for phrase in p['phrases']) + ', ' + str(p['distance']) + ')'}
    return C.finish(result, SPEC)
