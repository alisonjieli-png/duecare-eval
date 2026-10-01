"""Compute raw term-frequency times natural-log N/df weights; ubiquitous terms have zero weight and empty collections return empty maps."""
from . import _common as C

SPEC = C.spec("tfidf_vectors", "Compute raw term-frequency times natural-log N/df weights; ubiquitous terms have zero weight and empty collections return empty maps.",
    {'documents': C.DOCS}, {'idf': C.mapping(C.N), 'vectors': C.mapping(C.mapping(C.N))},
    {"documents": [{"id": "a", "text": "red"}, {"id": "b", "text": "blue"}]}, {"idf": {"blue": 0.69314718056, "red": 0.69314718056}, "vectors": {"a": {"red": 0.69314718056}, "b": {"blue": 0.69314718056}}}, sources=["tfidf"])


def run(payload: dict):
    p = C.check(payload, SPEC)
    idf, vectors = C.tfidf(p['documents'])
    result = {'idf': {term: round(weight, 12) for term, weight in idf.items()}, 'vectors': {identifier: {term: round(weight, 12) for term, weight in vector.items()} for identifier, vector in vectors.items()}}
    return C.finish(result, SPEC)
