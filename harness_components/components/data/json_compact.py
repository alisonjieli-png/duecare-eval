"""Serialize finite JSON values without optional whitespace, preserving object insertion order."""
from . import _shared as C

SPEC = C.spec("json_compact", "Serialize finite JSON values without optional whitespace, preserving object insertion order.",
    {'value': C.ANY}, {'text': C.S},
    {"value": {"x": [1, True]}}, {"text": "{\"x\":[1,true]}"}, [C.JSON_SOURCE])


def run(payload: dict) -> dict:
    p = C.check(payload, SPEC)
    result = {'text': C.compact(p['value'])}
    return C.finish(result, SPEC)
