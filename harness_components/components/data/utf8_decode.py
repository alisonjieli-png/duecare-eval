"""Decode integer bytes as strict UTF-8; retain a decoded BOM and reject malformed byte sequences."""
from . import _shared as C

SPEC = C.spec("utf8_decode", "Decode integer bytes as strict UTF-8; retain a decoded BOM and reject malformed byte sequences.",
    {'bytes': C.BYTES}, {'text': C.S},
    {"bytes": [99, 97, 102, 195, 169]}, {"text": "café"}, [C.BYTES_SOURCE])


def run(payload: dict) -> dict:
    p = C.check(payload, SPEC)
    try:
        text = bytes(p['bytes']).decode('utf-8', errors='strict')
    except UnicodeDecodeError as exc:
        raise ValueError('invalid_utf8') from exc
    result = {'text': text}
    return C.finish(result, SPEC)
