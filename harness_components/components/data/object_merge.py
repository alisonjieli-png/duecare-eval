"""Deep-merge two objects; right-hand values replace left scalars or arrays, and nested objects merge."""
from . import _shared as C

SPEC = C.spec("object_merge", "Deep-merge two objects; right-hand values replace left scalars or arrays, and nested objects merge.",
    {'left': C.O, 'right': C.O}, {'object': C.O},
    {"left": {"a": {"x": 1}, "b": [1]}, "right": {"a": {"y": 2}, "b": [3]}}, {"object": {"a": {"x": 1, "y": 2}, "b": [3]}}, [C.JSON_SOURCE])


def run(payload: dict) -> dict:
    p = C.check(payload, SPEC)
    result = {'object': C.merge_objects(p['left'], p['right'])}
    return C.finish(result, SPEC)
