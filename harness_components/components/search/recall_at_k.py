"""Compute relevant hits in the top k divided by all unique known relevant IDs; an empty relevance set reports zero with denominator zero."""
from . import _common as C

SPEC = C.spec("recall_at_k", "Compute relevant hits in the top k divided by all unique known relevant IDs; an empty relevance set reports zero with denominator zero.",
    {'retrieved': C.IDS, 'relevant': C.IDS, 'k': C.I}, {'recall': C.N, 'hits': C.I, 'denominator': C.I},
    {"retrieved": ["a", "b"], "relevant": ["b", "c"], "k": 2}, {"recall": 0.5, "hits": 1, "denominator": 2}, sources=["metrics"])


def run(payload: dict):
    p = C.check(payload, SPEC)
    wanted = C.rank_ids(p['retrieved'], p['relevant'])
    hits = sum(identifier in wanted for identifier in p['retrieved'][:p['k']])
    result = {'recall': hits / len(wanted) if wanted else 0.0, 'hits': hits, 'denominator': len(wanted)}
    return C.finish(result, SPEC)
