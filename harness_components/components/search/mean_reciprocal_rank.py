"""Average reciprocal ranks across all supplied query judgments, including queries with no hits; an empty query population reports zero with query_count zero."""
from . import _common as C

SPEC = C.spec("mean_reciprocal_rank", "Average reciprocal ranks across all supplied query judgments, including queries with no hits; an empty query population reports zero with query_count zero.",
    {'queries': C.arr(C.obj({'retrieved': C.IDS, 'relevant': C.IDS}))}, {'mrr': C.N, 'reciprocal_ranks': C.arr(C.N), 'query_count': C.I},
    {"queries": [{"retrieved": ["a", "b"], "relevant": ["b"]}, {"retrieved": ["x"], "relevant": ["z"]}]}, {"mrr": 0.25, "reciprocal_ranks": [0.5, 0], "query_count": 2}, sources=["metrics"])


def run(payload: dict):
    p = C.check(payload, SPEC)
    values = [C.rr(query['retrieved'], query['relevant']) for query in p['queries']]
    result = {'mrr': C.math.fsum(values) / len(values) if values else 0.0, 'reciprocal_ranks': values, 'query_count': len(values)}
    return C.finish(result, SPEC)
