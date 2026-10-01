"""Keep the first record for each exact typed tuple of selected existing fields."""
from . import _shared as C

SPEC = C.spec("records_deduplicate", "Keep the first record for each exact typed tuple of selected existing fields.",
    {'records': C.RECORDS, 'keys': C.STRINGS}, {'records': C.RECORDS, 'removed': C.I},
    {"records": [{"id": 1, "v": "first"}, {"id": 1, "v": "later"}, {"id": 2, "v": "other"}], "keys": ["id"]}, {"records": [{"id": 1, "v": "first"}, {"id": 2, "v": "other"}], "removed": 1}, [C.JSON_SOURCE])


def run(payload: dict) -> dict:
    p = C.check(payload, SPEC)
    C.require(bool(p['keys']) and len(p['keys']) == len(set(p['keys'])), 'unique_nonempty_keys_required')
    C.record_keys(p['records'], p['keys'])
    seen, rows = set(), []
    for row in p['records']:
        key = C.identity([row[name] for name in p['keys']])
        if key not in seen:
            seen.add(key)
            rows.append(row)
    result = {'records': rows, 'removed': len(p['records']) - len(rows)}
    return C.finish(result, SPEC)
