"""Normalize a query by Unicode NFKC, casefold and whitespace collapse; original text is not modified."""
from . import _common as C

SPEC = C.spec("normalize_query", "Normalize a query by Unicode NFKC, casefold and whitespace collapse; original text is not modified.",
    {'text': C.S}, {'query': C.S},
    {"text": "  Ｃafé\tStraße "}, {"query": "café strasse"}, sources=["unicode"])


def run(payload: dict):
    p = C.check(payload, SPEC)
    result = {'query': ' '.join(C.normalized(p['text']).split())}
    return C.finish(result, SPEC)
