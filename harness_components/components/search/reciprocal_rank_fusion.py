"""Fuse unique-ID ranked lists using sum(1/(k+one_based_rank)); missing documents contribute zero, duplicate IDs within a list are rejected and score ties use document ID."""
from . import _common as C

SPEC = C.spec("reciprocal_rank_fusion", "Fuse unique-ID ranked lists using sum(1/(k+one_based_rank)); missing documents contribute zero, duplicate IDs within a list are rejected and score ties use document ID.",
    {'rankings': C.arr(C.IDS), 'k': C.number(0), 'limit': C.I}, {'results': C.RANKING},
    {"rankings": [["a", "b"], ["b", "a"]], "k": 0, "limit": 2}, {"results": [{"id": "a", "score": 1.5, "rank": 1}, {"id": "b", "score": 1.5, "rank": 2}]}, sources=["rrf"])


def run(payload: dict):
    p = C.check(payload, SPEC)
    contributions = {}
    for ranking in p['rankings']:
        for rank, identifier in enumerate(ranking, 1): contributions.setdefault(identifier, []).append(1.0 / (p['k'] + rank))
    scores = {identifier: C.math.fsum(values) for identifier, values in contributions.items()}
    result = {'results': C.ranking(scores, p['limit'])}
    return C.finish(result, SPEC)
