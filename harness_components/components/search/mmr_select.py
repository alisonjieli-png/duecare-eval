"""Greedily select supplied numeric vectors using lambda*cos(query,doc)-(1-lambda)*max_cos(doc,selected); empty-selected redundancy is zero, ties use ID and scores are reported to 12 decimals."""
from . import _common as C

SPEC = C.spec("mmr_select", "Greedily select supplied numeric vectors using lambda*cos(query,doc)-(1-lambda)*max_cos(doc,selected); empty-selected redundancy is zero, ties use ID and scores are reported to 12 decimals.",
    {'query_vector': C.VECTOR, 'documents': C.arr(C.obj({'id': {'type': 'string', 'minLength': 1}, 'vector': C.VECTOR})), 'lambda_weight': C.number(0, 1), 'limit': C.I}, {'selected': C.arr(C.obj({'id': C.S, 'rank': C.integer(1), 'relevance': C.N, 'redundancy': C.N, 'mmr_score': C.N}))},
    {"query_vector": [1, 0], "documents": [{"id": "a", "vector": [1, 0]}, {"id": "b", "vector": [0, 1]}], "lambda_weight": 1, "limit": 2}, {"selected": [{"id": "a", "rank": 1, "relevance": 1, "redundancy": 0, "mmr_score": 1}, {"id": "b", "rank": 2, "relevance": 0, "redundancy": 0, "mmr_score": 0}]}, sources=["mmr", "cosine"])


def run(payload: dict):
    p = C.check(payload, SPEC)
    rows = p['documents']; C.require(len({row['id'] for row in rows}) == len(rows), 'duplicate document ID')
    C.require(all(len(row['vector']) == len(p['query_vector']) for row in rows), 'vector dimensions differ')
    remaining = {row['id']: row['vector'] for row in rows}; chosen = []; selected_vectors = []
    while remaining and len(chosen) < p['limit']:
        candidates = []
        for identifier, vector in remaining.items():
            relevance = C.cosine(p['query_vector'], vector)
            redundancy = max((C.cosine(vector, previous) for previous in selected_vectors), default=0.0)
            score = p['lambda_weight'] * relevance - (1 - p['lambda_weight']) * redundancy
            candidates.append((identifier, score, relevance, redundancy))
        identifier, score, relevance, redundancy = min(candidates, key=lambda row: (-row[1], row[0]))
        selected_vectors.append(remaining.pop(identifier))
        chosen.append({'id': identifier, 'rank': len(chosen) + 1, 'relevance': round(relevance, 12), 'redundancy': round(redundancy, 12), 'mmr_score': round(score, 12)})
    result = {'selected': chosen}
    return C.finish(result, SPEC)
