"""Compute set Jaccard similarity of supplied string tokens, ignoring duplicates; two empty sets have similarity one."""
from . import _common as C

SPEC = C.spec("jaccard_similarity", "Compute set Jaccard similarity of supplied string tokens, ignoring duplicates; two empty sets have similarity one.",
    {'a': C.STRINGS, 'b': C.STRINGS}, {'similarity': C.N, 'intersection_size': C.I, 'union_size': C.I},
    {"a": ["a", "b", "b"], "b": ["b", "c"]}, {"similarity": 0.3333333333333333, "intersection_size": 1, "union_size": 3}, sources=["set"])


def run(payload: dict):
    p = C.check(payload, SPEC)
    a, b = set(p['a']), set(p['b']); union = a | b; overlap = a & b
    result = {'similarity': len(overlap) / len(union) if union else 1.0, 'intersection_size': len(overlap), 'union_size': len(union)}
    return C.finish(result, SPEC)
