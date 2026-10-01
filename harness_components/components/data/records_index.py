"""Index records by an existing unique string field; refuse duplicate or nonstring keys."""
from . import _shared as C

SPEC = C.spec("records_index", "Index records by an existing unique string field; refuse duplicate or nonstring keys.",
    {'records': C.RECORDS, 'key': C.S}, {'index': C.O},
    {"records": [{"id": "x", "v": 2}], "key": "id"}, {"index": {"x": {"id": "x", "v": 2}}}, [C.JSON_SOURCE])


def run(payload: dict) -> dict:
    p = C.check(payload, SPEC)
    C.record_keys(p['records'], [p['key']])
    keys = [row[p['key']] for row in p['records']]
    C.require(all(type(key) is str for key in keys), 'string_index_key_required')
    C.require(len(keys) == len(set(keys)), 'duplicate_index_key')
    result = {'index': dict(zip(keys, p['records']))}
    return C.finish(result, SPEC)
