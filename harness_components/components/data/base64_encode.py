"""Encode integer bytes with the standard Base64 alphabet and canonical padding."""
from . import _shared as C
import base64

SPEC = C.spec("base64_encode", "Encode integer bytes with the standard Base64 alphabet and canonical padding.",
    {'bytes': C.BYTES}, {'text': C.S},
    {"bytes": [97, 98, 99]}, {"text": "YWJj"}, ['https://docs.python.org/3/library/base64.html'])


def run(payload: dict) -> dict:
    p = C.check(payload, SPEC)
    result = {'text': base64.b64encode(bytes(p['bytes'])).decode('ascii')}
    return C.finish(result, SPEC)
