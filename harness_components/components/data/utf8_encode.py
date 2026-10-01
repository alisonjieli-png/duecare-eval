"""Encode a Unicode scalar string as integer UTF-8 bytes without changing normalization."""
from . import _shared as C

SPEC = C.spec("utf8_encode", "Encode a Unicode scalar string as integer UTF-8 bytes without changing normalization.",
    {'text': C.S}, {'bytes': C.BYTES},
    {"text": "café"}, {"bytes": [99, 97, 102, 195, 169]}, [C.BYTES_SOURCE])


def run(payload: dict) -> dict:
    p = C.check(payload, SPEC)
    result = {'bytes': list(p['text'].encode('utf-8'))}
    return C.finish(result, SPEC)
