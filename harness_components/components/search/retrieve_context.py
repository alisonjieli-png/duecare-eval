"""Expand selected passage IDs by neighbouring list positions; return each original passage once in corpus order and reject unknown IDs."""
from . import _common as C

SPEC = C.spec("retrieve_context", "Expand selected passage IDs by neighbouring list positions; return each original passage once in corpus order and reject unknown IDs.",
    {'passages': C.DOCS, 'selected_ids': C.IDS, 'before': C.I, 'after': C.I}, {'passages': C.DOCS},
    {"passages": [{"id": "a", "text": "one"}, {"id": "b", "text": "two"}, {"id": "c", "text": "three"}], "selected_ids": ["b"], "before": 1, "after": 0}, {"passages": [{"id": "a", "text": "one"}, {"id": "b", "text": "two"}]}, sources=["python"])


def run(payload: dict):
    p = C.check(payload, SPEC)
    rows = C.documents(p['passages']); lookup = {row['id']: i for i, row in enumerate(rows)}
    C.require(set(p['selected_ids']) <= set(lookup), 'unknown selected passage ID')
    positions = set()
    for identifier in p['selected_ids']:
        index = lookup[identifier]
        positions.update(range(max(0, index - p['before']), min(len(rows), index + p['after'] + 1)))
    result = {'passages': [dict(row) for i, row in enumerate(rows) if i in positions]}
    return C.finish(result, SPEC)
