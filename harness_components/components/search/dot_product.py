"""Compute the finite numeric dot product of equally sized supplied vectors; empty vectors have product zero."""
from . import _common as C

SPEC = C.spec("dot_product", "Compute the finite numeric dot product of equally sized supplied vectors; empty vectors have product zero.",
    {'a': C.VECTOR, 'b': C.VECTOR}, {'dot_product': C.N},
    {"a": [1, 2], "b": [3, 4]}, {"dot_product": 11}, sources=["math", "cosine"])


def run(payload: dict):
    p = C.check(payload, SPEC)
    C.require(len(p['a']) == len(p['b']), 'vector dimensions differ')
    result = {'dot_product': C.math.fsum(a * b for a, b in zip(p['a'], p['b']))}
    return C.finish(result, SPEC)
