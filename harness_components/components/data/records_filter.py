"""Select records whose existing field equals a supplied JSON value using type-sensitive comparison."""
from . import _shared as C

SPEC = C.spec("records_filter", "Select records whose existing field equals a supplied JSON value using type-sensitive comparison.",
    {'records': C.RECORDS, 'key': C.S, 'value': C.ANY}, {'records': C.RECORDS},
    {"records": [{"v": 1}, {"v": True}], "key": "v", "value": 1}, {"records": [{"v": 1}]}, [C.JSON_SOURCE])


def run(payload: dict) -> dict:
    p = C.check(payload, SPEC)
    C.record_keys(p['records'], [p['key']])
    expected = C.identity(p['value'])
    result = {'records': [row for row in p['records'] if C.identity(row[p['key']]) == expected]}
    return C.finish(result, SPEC)
