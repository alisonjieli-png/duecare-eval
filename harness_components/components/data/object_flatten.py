"""Flatten JSON leaves and empty containers into a map keyed by escaped JSON Pointers."""
from . import _shared as C

SPEC = C.spec("object_flatten", "Flatten JSON leaves and empty containers into a map keyed by escaped JSON Pointers.",
    {'value': C.ANY}, {'leaves': C.O},
    {"value": {"a/b": [2], "empty": {}}}, {"leaves": {"/a~1b/0": 2, "/empty": {}}}, [C.POINTER_SOURCE, C.JSON_SOURCE])


def run(payload: dict) -> dict:
    p = C.check(payload, SPEC)
    result = {'leaves': C.flatten(p['value'])}
    return C.finish(result, SPEC)
