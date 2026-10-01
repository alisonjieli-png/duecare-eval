"""Compute Euclidean distance between equal-length finite vectors; no embedding model or index is loaded."""
from . import _common as C

SPEC = C.spec("l2_distance", "Compute Euclidean distance between equal-length finite vectors; no embedding model or index is loaded.",
    {'a': C.VECTOR, 'b': C.VECTOR}, {'distance': C.N},
    {"a": [0, 0], "b": [3, 4]}, {"distance": 5}, sources=["math"])


def run(payload: dict):
    p = C.check(payload, SPEC)
    C.require(len(p['a']) == len(p['b']), 'vector dimensions differ')
    result = {'distance': C.math.hypot(*(a - b for a, b in zip(p['a'], p['b'])))}
    return C.finish(result, SPEC)
