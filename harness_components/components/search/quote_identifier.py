"""Validate an ASCII SQL identifier and double-quote it, including reserved words; reject dotted names, expressions, comments and caller SQL syntax."""
from . import _common as C

SPEC = C.spec("quote_identifier", "Validate an ASCII SQL identifier and double-quote it, including reserved words; reject dotted names, expressions, comments and caller SQL syntax.",
    {'name': C.IDENTIFIER}, {'identifier': C.S},
    {"name": "order"}, {"identifier": "\"order\""}, sources=["sqlite"])


def run(payload: dict):
    p = C.check(payload, SPEC)
    result = {'identifier': C.quoted_identifier(p['name'])}
    return C.finish(result, SPEC)
