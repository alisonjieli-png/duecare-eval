"""Return reciprocal one-based rank of the first relevant result, or zero when none is retrieved; duplicate IDs are rejected."""
from . import _common as C

SPEC = C.spec("reciprocal_rank", "Return reciprocal one-based rank of the first relevant result, or zero when none is retrieved; duplicate IDs are rejected.",
    {'retrieved': C.IDS, 'relevant': C.IDS}, {'reciprocal_rank': C.N},
    {"retrieved": ["a", "b", "c"], "relevant": ["b", "c"]}, {"reciprocal_rank": 0.5}, sources=["metrics"])


def run(payload: dict):
    p = C.check(payload, SPEC)
    result = {'reciprocal_rank': C.rr(p['retrieved'], p['relevant'])}
    return C.finish(result, SPEC)
