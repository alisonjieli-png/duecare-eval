"""Rank by cosine similarity of raw-tf log(N/df) query/document vectors; keep zero scores, use lexicographic ID tie breaks, round reported scores to 12 decimals."""
from . import _common as C

SPEC = C.spec("tfidf_rank", "Rank by cosine similarity of raw-tf log(N/df) query/document vectors; keep zero scores, use lexicographic ID tie breaks, round reported scores to 12 decimals.",
    {'documents': C.DOCS, 'query': C.S, 'limit': C.I}, {'results': C.RANKING},
    {"documents": [{"id": "a", "text": "red"}, {"id": "b", "text": "blue"}], "query": "red", "limit": 2}, {"results": [{"id": "a", "score": 1, "rank": 1}, {"id": "b", "score": 0, "rank": 2}]}, sources=["tfidf", "cosine"])


def run(payload: dict):
    p = C.check(payload, SPEC)
    idf, vectors = C.tfidf(p['documents'])
    query = {term: count * idf.get(term, 0.0) for term, count in C.Counter(C.terms(p['query'])).items()}
    scores = {identifier: C.sparse_cosine(vector, query) for identifier, vector in vectors.items()}
    result = {'results': C.ranking(scores, p['limit'])}
    return C.finish(result, SPEC)
