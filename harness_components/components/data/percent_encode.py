"""Percent-encode a UTF-8 string as a URL component; slashes and spaces are encoded, and no form-plus conversion is used."""
from . import _shared as C
from urllib.parse import quote

SPEC = C.spec("percent_encode", "Percent-encode a UTF-8 string as a URL component; slashes and spaces are encoded, and no form-plus conversion is used.",
    {'text': C.S}, {'text': C.S},
    {"text": "café /+"}, {"text": "caf%C3%A9%20%2F%2B"}, [C.URL_SOURCE])


def run(payload: dict) -> dict:
    p = C.check(payload, SPEC)
    result = {'text': quote(p['text'], safe='', encoding='utf-8', errors='strict')}
    return C.finish(result, SPEC)
