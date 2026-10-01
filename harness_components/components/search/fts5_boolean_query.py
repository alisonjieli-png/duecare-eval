"""Combine literal token-bearing phrases with a fixed AND or OR operator and parentheses; embedded operators remain quoted phrase data."""
from . import _common as C

SPEC = C.spec("fts5_boolean_query", "Combine literal token-bearing phrases with a fixed AND or OR operator and parentheses; embedded operators remain quoted phrase data.",
    {'phrases': C.arr(C.S, 1), 'operator': C.choice('AND', 'OR')}, {'query': C.S},
    {"phrases": ["red blue", "green"], "operator": "OR"}, {"query": "(\"red blue\" OR \"green\")"}, sources=["fts5"])


def run(payload: dict):
    p = C.check(payload, SPEC)
    C.require(all(any(char.isalnum() for char in phrase) for phrase in p['phrases']), 'each phrase needs alphanumeric content')
    result = {'query': '(' + (' ' + p['operator'] + ' ').join(C.fts_quote(phrase) for phrase in p['phrases']) + ')'}
    return C.finish(result, SPEC)
