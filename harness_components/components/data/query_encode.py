"""Encode an ordered list of string pairs as form query text while preserving duplicate keys."""
from . import _shared as C
from urllib.parse import urlencode

SPEC = C.spec("query_encode", "Encode an ordered list of string pairs as form query text while preserving duplicate keys.",
    {'pairs': C.PAIRS}, {'query': C.S},
    {"pairs": [["a", "1"], ["a", "2"], ["q", "a b"]]}, {"query": "a=1&a=2&q=a+b"}, [C.URL_SOURCE])


def run(payload: dict) -> dict:
    p = C.check(payload, SPEC)
    result = {'query': urlencode(C.string_pairs(p['pairs']), encoding='utf-8', errors='strict')}
    return C.finish(result, SPEC)
