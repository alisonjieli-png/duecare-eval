"""Decode percent escapes as strict UTF-8, leaving literal plus signs unchanged."""
from . import _shared as C

SPEC = C.spec("percent_decode", "Decode percent escapes as strict UTF-8, leaving literal plus signs unchanged.",
    {'text': C.S}, {'text': C.S},
    {"text": "caf%C3%A9+%2B"}, {"text": "café++"}, [C.URL_SOURCE])


def run(payload: dict) -> dict:
    p = C.check(payload, SPEC)
    result = {'text': C.percent_decode(p['text'])}
    return C.finish(result, SPEC)
