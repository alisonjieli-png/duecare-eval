"""Group records by a JSON-valued field with type-sensitive identity and first-seen group order."""
from . import _shared as C

SPEC = C.spec("records_group", "Group records by a JSON-valued field with type-sensitive identity and first-seen group order.",
    {'records': C.RECORDS, 'key': C.S}, {'groups': C.A},
    {"records": [{"k": "a", "v": 1}, {"k": "a", "v": 2}], "key": "k"}, {"groups": [{"value": "a", "records": [{"k": "a", "v": 1}, {"k": "a", "v": 2}]}]}, [C.JSON_SOURCE])


def run(payload: dict) -> dict:
    p = C.check(payload, SPEC)
    C.record_keys(p['records'], [p['key']])
    groups = {}
    for row in p['records']:
        value = row[p['key']]
        key = C.identity(value)
        groups.setdefault(key, {'value': value, 'records': []})['records'].append(row)
    result = {'groups': list(groups.values())}
    return C.finish(result, SPEC)
