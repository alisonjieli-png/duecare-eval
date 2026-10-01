"""Select existing object keys in the requested order; reject missing or repeated keys."""
from . import _shared as C

SPEC = C.spec("object_project", "Select existing object keys in the requested order; reject missing or repeated keys.",
    {'object': C.O, 'keys': C.STRINGS}, {'object': C.O},
    {"object": {"a": 1, "b": 2}, "keys": ["b"]}, {"object": {"b": 2}}, [C.JSON_SOURCE])


def run(payload: dict) -> dict:
    p = C.check(payload, SPEC)
    C.keys_present(p['object'], p['keys'])
    result = {'object': {key: p['object'][key] for key in p['keys']}}
    return C.finish(result, SPEC)
