"""Resolve a JSON Pointer against provided data; missing members and noncanonical array indices fail."""
from . import _shared as C

SPEC = C.spec("pointer_get", "Resolve a JSON Pointer against provided data; missing members and noncanonical array indices fail.",
    {'value': C.ANY, 'pointer': C.S}, {'value': C.ANY},
    {"value": {"a/b": [8]}, "pointer": "/a~1b/0"}, {"value": 8}, [C.POINTER_SOURCE])


def run(payload: dict) -> dict:
    p = C.check(payload, SPEC)
    result = {'value': C.pointer_get(p['value'], p['pointer'])}
    return C.finish(result, SPEC)
