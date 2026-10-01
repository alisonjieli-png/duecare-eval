"""Escape one JSON Pointer token without normalizing Unicode or interpreting percent escapes."""
from . import _shared as C

SPEC = C.spec("pointer_escape", "Escape one JSON Pointer token without normalizing Unicode or interpreting percent escapes.",
    {'token': C.S}, {'token': C.S},
    {"token": "a/~b"}, {"token": "a~1~0b"}, [C.POINTER_SOURCE])


def run(payload: dict) -> dict:
    p = C.check(payload, SPEC)
    result = {'token': C.pointer_escape(p['token'])}
    return C.finish(result, SPEC)
