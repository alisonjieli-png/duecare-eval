"""Extract one existing field from every record while retaining order and value types."""
from . import _shared as C

SPEC = C.spec("records_pluck", "Extract one existing field from every record while retaining order and value types.",
    {'records': C.RECORDS, 'key': C.S}, {'values': C.A},
    {"records": [{"a": 1}, {"a": 2}], "key": "a"}, {"values": [1, 2]}, [C.JSON_SOURCE])


def run(payload: dict) -> dict:
    p = C.check(payload, SPEC)
    C.record_keys(p['records'], [p['key']])
    result = {'values': [row[p['key']] for row in p['records']]}
    return C.finish(result, SPEC)
