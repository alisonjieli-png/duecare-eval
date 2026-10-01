"""Parse form-encoded query pairs preserving duplicate keys/order and blank values; plus means space and empty segments are ignored."""
from . import _shared as C

SPEC = C.spec("query_parse", "Parse form-encoded query pairs preserving duplicate keys/order and blank values; plus means space and empty segments are ignored.",
    {'query': C.S}, {'pairs': C.ROWS},
    {"query": "a=1&a=2&blank=&q=a+b"}, {"pairs": [["a", "1"], ["a", "2"], ["blank", ""], ["q", "a b"]]}, [C.URL_SOURCE])


def run(payload: dict) -> dict:
    p = C.check(payload, SPEC)
    result = {'pairs': C.query_pairs(p['query'])}
    return C.finish(result, SPEC)
