"""Build an object from ordered string-key/value pairs, rejecting duplicate keys."""
from . import _shared as C

SPEC = C.spec("object_from_pairs", "Build an object from ordered string-key/value pairs, rejecting duplicate keys.",
    {'pairs': C.A}, {'object': C.O},
    {"pairs": [["a", 1], ["b", False]]}, {"object": {"a": 1, "b": False}}, [C.JSON_SOURCE])


def run(payload: dict) -> dict:
    p = C.check(payload, SPEC)
    result = {'object': C.pairs_object(p['pairs'])}
    return C.finish(result, SPEC)
