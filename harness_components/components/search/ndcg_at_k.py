"""Normalize linear-gain DCG by the ideal top-k ordering of all supplied judgments; unjudged IDs contribute zero, duplicate ranks are rejected and zero ideal gain returns zero."""
from . import _common as C

SPEC = C.spec("ndcg_at_k", "Normalize linear-gain DCG by the ideal top-k ordering of all supplied judgments; unjudged IDs contribute zero, duplicate ranks are rejected and zero ideal gain returns zero.",
    {'retrieved': C.IDS, 'relevance': C.mapping(C.number(0)), 'k': C.I}, {'ndcg': C.N, 'dcg': C.N, 'ideal_dcg': C.N, 'evaluated_ranks': C.I},
    {"retrieved": ["a", "b"], "relevance": {"a": 3, "b": 0}, "k": 2}, {"ndcg": 1.0, "dcg": 3.0, "ideal_dcg": 3.0, "evaluated_ranks": 2}, sources=["metrics"])


def run(payload: dict):
    p = C.check(payload, SPEC)
    C.require(all(p['relevance']), 'relevance IDs must be nonempty')
    gains = [p['relevance'].get(identifier, 0.0) for identifier in p['retrieved']]
    actual = C.dcg(gains, p['k']); ideal = C.dcg(sorted(p['relevance'].values(), reverse=True), p['k'])
    result = {'ndcg': actual / ideal if ideal else 0.0, 'dcg': actual, 'ideal_dcg': ideal, 'evaluated_ranks': min(p['k'], len(p['retrieved']))}
    return C.finish(result, SPEC)
