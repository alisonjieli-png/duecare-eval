"""Average precision at each relevant hit over the full known relevant population, preserving the penalty for relevant documents never returned; empty relevance reports zero."""
from . import _common as C

SPEC = C.spec("average_precision", "Average precision at each relevant hit over the full known relevant population, preserving the penalty for relevant documents never returned; empty relevance reports zero.",
    {'retrieved': C.IDS, 'relevant': C.IDS}, {'average_precision': C.N, 'precision_sum': C.N, 'retrieved_relevant': C.I, 'relevant_total': C.I},
    {"retrieved": ["a", "b"], "relevant": ["a", "c"]}, {"average_precision": 0.5, "precision_sum": 1.0, "retrieved_relevant": 1, "relevant_total": 2}, sources=["metrics"])


def run(payload: dict):
    p = C.check(payload, SPEC)
    wanted = C.rank_ids(p['retrieved'], p['relevant']); hits = 0; precisions = []
    for rank, identifier in enumerate(p['retrieved'], 1):
        if identifier in wanted:
            hits += 1; precisions.append(hits / rank)
    total = C.math.fsum(precisions)
    result = {'average_precision': total / len(wanted) if wanted else 0.0, 'precision_sum': total, 'retrieved_relevant': hits, 'relevant_total': len(wanted)}
    return C.finish(result, SPEC)
