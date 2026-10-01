"""Encode integer bytes as lowercase hexadecimal with exactly two characters per byte."""
from . import _shared as C

SPEC = C.spec("hex_encode", "Encode integer bytes as lowercase hexadecimal with exactly two characters per byte.",
    {'bytes': C.BYTES}, {'text': C.S},
    {"bytes": [0, 15, 255]}, {"text": "000fff"}, [C.BYTES_SOURCE])


def run(payload: dict) -> dict:
    p = C.check(payload, SPEC)
    result = {'text': bytes(p['bytes']).hex()}
    return C.finish(result, SPEC)
