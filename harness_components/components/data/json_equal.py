"""Compare finite JSON values with order-insensitive objects and type-sensitive scalar representations."""
from . import _shared as C

SPEC = C.spec("json_equal", "Compare finite JSON values with order-insensitive objects and type-sensitive scalar representations.",
    {'left': C.ANY, 'right': C.ANY}, {'equal': C.B},
    {"left": 1, "right": True}, {"equal": False}, [C.JSON_SOURCE])


def run(payload: dict) -> dict:
    p = C.check(payload, SPEC)
    result = {'equal': C.identity(p['left']) == C.identity(p['right'])}
    return C.finish(result, SPEC)
