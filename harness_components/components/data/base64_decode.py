"""Decode strictly canonical standard Base64, rejecting whitespace, extraneous padding and nonzero unused bits."""
from . import _shared as C
import base64
import binascii

SPEC = C.spec("base64_decode", "Decode strictly canonical standard Base64, rejecting whitespace, extraneous padding and nonzero unused bits.",
    {'text': C.S}, {'bytes': C.BYTES},
    {"text": "YQ=="}, {"bytes": [97]}, ['https://docs.python.org/3/library/base64.html'])


def run(payload: dict) -> dict:
    p = C.check(payload, SPEC)
    try:
        raw = base64.b64decode(p['text'], validate=True)
    except (ValueError, binascii.Error) as exc:
        raise ValueError('invalid_base64') from exc
    C.require(base64.b64encode(raw).decode('ascii') == p['text'], 'noncanonical_base64')
    result = {'bytes': list(raw)}
    return C.finish(result, SPEC)
