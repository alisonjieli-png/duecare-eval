"""Quote an entire FTS5 phrase by doubling embedded double quotes; return query data for a separately parameterized MATCH expression."""
from . import _common as C

SPEC = C.spec("fts5_quote_phrase", "Quote an entire FTS5 phrase by doubling embedded double quotes; return query data for a separately parameterized MATCH expression.",
    {'text': C.S}, {'query': C.S},
    {"text": "alpha \"beta\""}, {"query": "\"alpha \"\"beta\"\"\""}, sources=["fts5"])


def run(payload: dict):
    p = C.check(payload, SPEC)
    result = {'query': C.fts_quote(p['text'])}
    return C.finish(result, SPEC)
