"""Find case-sensitive literal occurrences in identified in-memory records, counting overlapping hits and retaining exact spans."""
from . import _common as C

SPEC = C.spec("grep_records", "Find case-sensitive literal occurrences in identified in-memory records, counting overlapping hits and retaining exact spans.",
    {'records': C.DOCS, 'needle': C.S}, {'records': C.arr(C.obj({'id': C.S, 'count': C.I, 'matches': C.arr(C.SPAN)}))},
    {"records": [{"id": "a", "text": "banana"}, {"id": "b", "text": "pear"}], "needle": "ana"}, {"records": [{"id": "a", "count": 2, "matches": [{"start": 1, "end": 4}, {"start": 3, "end": 6}]}]}, sources=["python"])


def run(payload: dict):
    p = C.check(payload, SPEC)
    C.documents(p['records'])
    found = []
    for row in p['records']:
        spans = C.occurrences(row['text'], p['needle'])
        if spans: found.append({'id': row['id'], 'count': len(spans), 'matches': spans})
    result = {'records': found}
    return C.finish(result, SPEC)
