"""Convert equally shaped records into columns, preserving record and first-record key order."""
from . import _shared as C

SPEC = C.spec("records_transpose", "Convert equally shaped records into columns, preserving record and first-record key order.",
    {'records': C.RECORDS}, {'columns': C.O},
    {"records": [{"a": 1, "b": 2}, {"a": 3, "b": 4}]}, {"columns": {"a": [1, 3], "b": [2, 4]}}, [C.JSON_SOURCE])


def run(payload: dict) -> dict:
    p = C.check(payload, SPEC)
    keys = list(p['records'][0]) if p['records'] else []
    C.require(all(set(row) == set(keys) for row in p['records']), 'record_columns_mismatch')
    result = {'columns': {key: [row[key] for row in p['records']] for key in keys}}
    return C.finish(result, SPEC)
