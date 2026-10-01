"""Compute scale-stable cosine similarity for equal-length finite numeric vectors; a zero or empty vector has similarity zero."""
from . import _common as C

SPEC = C.spec("cosine_similarity", "Compute scale-stable cosine similarity for equal-length finite numeric vectors; a zero or empty vector has similarity zero.",
    {'a': C.VECTOR, 'b': C.VECTOR}, {'similarity': C.N},
    {"a": [1, 0], "b": [0, 1]}, {"similarity": 0}, sources=["cosine", "math"])


def run(payload: dict):
    p = C.check(payload, SPEC)
    result = {'similarity': C.cosine(p['a'], p['b'])}
    return C.finish(result, SPEC)
