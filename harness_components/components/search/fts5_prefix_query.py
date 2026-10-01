"""Build a quoted single alphanumeric-token FTS5 prefix query with the wildcard outside quotes; caller operators and punctuation are rejected."""
from . import _common as C

SPEC = C.spec("fts5_prefix_query", "Build a quoted single alphanumeric-token FTS5 prefix query with the wildcard outside quotes; caller operators and punctuation are rejected.",
    {'prefix': C.S}, {'query': C.S},
    {"prefix": "café"}, {"query": "\"café\"*"}, sources=["fts5"])


def run(payload: dict):
    p = C.check(payload, SPEC)
    C.require(bool(p['prefix']) and all(char.isalnum() for char in p['prefix']), 'prefix must be one nonempty alphanumeric token')
    result = {'query': C.fts_quote(p['prefix']) + '*'}
    return C.finish(result, SPEC)
