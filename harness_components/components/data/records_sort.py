"""Stably sort records by an existing string field in Unicode code-point order."""
from . import _shared as C

SPEC = C.spec("records_sort", "Stably sort records by an existing string field in Unicode code-point order.",
    {'records': C.RECORDS, 'key': C.S, 'reverse': C.B}, {'records': C.RECORDS},
    {"records": [{"name": "b"}, {"name": "a"}], "key": "name", "reverse": False}, {"records": [{"name": "a"}, {"name": "b"}]}, [C.JSON_SOURCE])


def run(payload: dict) -> dict:
    p = C.check(payload, SPEC)
    C.record_keys(p['records'], [p['key']])
    C.require(all(type(row[p['key']]) is str for row in p['records']), 'string_sort_key_required')
    result = {'records': sorted(p['records'], key=lambda row: row[p['key']], reverse=p['reverse'])}
    return C.finish(result, SPEC)
