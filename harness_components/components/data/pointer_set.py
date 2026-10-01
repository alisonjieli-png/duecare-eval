"""Return a copy replacing an existing JSON Pointer target; the empty pointer replaces the root."""
from . import _shared as C

SPEC = C.spec("pointer_set", "Return a copy replacing an existing JSON Pointer target; the empty pointer replaces the root.",
    {'value': C.ANY, 'pointer': C.S, 'replacement': C.ANY}, {'value': C.ANY},
    {"value": {"a": [1, 2]}, "pointer": "/a/1", "replacement": 9}, {"value": {"a": [1, 9]}}, [C.POINTER_SOURCE])


def run(payload: dict) -> dict:
    p = C.check(payload, SPEC)
    result = {'value': C.pointer_set(p['value'], p['pointer'], p['replacement'])}
    return C.finish(result, SPEC)
