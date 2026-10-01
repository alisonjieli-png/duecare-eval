"""Compute relevant hits divided by requested cutoff k; missing returned positions count as misses, duplicate IDs are rejected and k=0 reports zero with denominator zero."""
from . import _common as C

SPEC = C.spec("precision_at_k", "Compute relevant hits divided by requested cutoff k; missing returned positions count as misses, duplicate IDs are rejected and k=0 reports zero with denominator zero.",
    {'retrieved': C.IDS, 'relevant': C.IDS, 'k': C.I}, {'precision': C.N, 'hits': C.I, 'denominator': C.I, 'returned_at_k': C.I},
    {"retrieved": ["a", "b"], "relevant": ["b"], "k": 3}, {"precision": 0.3333333333333333, "hits": 1, "denominator": 3, "returned_at_k": 2}, sources=["metrics"])


def run(payload: dict):
    p = C.check(payload, SPEC)
    wanted = C.rank_ids(p['retrieved'], p['relevant']); returned = p['retrieved'][:p['k']]
    hits = sum(identifier in wanted for identifier in returned)
    result = {'precision': hits / p['k'] if p['k'] else 0.0, 'hits': hits, 'denominator': p['k'], 'returned_at_k': len(returned)}
    return C.finish(result, SPEC)
