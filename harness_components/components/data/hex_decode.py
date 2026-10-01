"""Decode even-length hexadecimal without allowing whitespace or prefixes; accept upper- or lowercase hex digits."""
from . import _shared as C
import re

SPEC = C.spec("hex_decode", "Decode even-length hexadecimal without allowing whitespace or prefixes; accept upper- or lowercase hex digits.",
    {'text': C.S}, {'bytes': C.BYTES},
    {"text": "00Af"}, {"bytes": [0, 175]}, [C.BYTES_SOURCE])


def run(payload: dict) -> dict:
    p = C.check(payload, SPEC)
    C.require(re.fullmatch(r'(?:[0-9A-Fa-f]{2})*', p['text']) is not None, 'invalid_hex')
    result = {'bytes': list(bytes.fromhex(p['text']))}
    return C.finish(result, SPEC)
