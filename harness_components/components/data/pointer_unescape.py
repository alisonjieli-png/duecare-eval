"""Decode one JSON Pointer token and reject invalid tilde escapes."""
from . import _shared as C

SPEC = C.spec("pointer_unescape", "Decode one JSON Pointer token and reject invalid tilde escapes.",
    {'token': C.S}, {'token': C.S},
    {"token": "~01"}, {"token": "~1"}, [C.POINTER_SOURCE])


def run(payload: dict) -> dict:
    p = C.check(payload, SPEC)
    result = {'token': C.pointer_unescape(p['token'])}
    return C.finish(result, SPEC)
