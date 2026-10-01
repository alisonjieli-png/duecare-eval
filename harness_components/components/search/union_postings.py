"""Return documents containing any normalized supplied term in original document order; empty terms return no documents."""
from . import _common as C

SPEC = C.spec("union_postings", "Return documents containing any normalized supplied term in original document order; empty terms return no documents.",
    {'index': C.INDEX, 'terms': C.STRINGS}, {'document_ids': C.IDS},
    {"index": {"document_ids": ["a", "b"], "lengths": {"a": 2, "b": 1}, "postings": {"blue": {"a": [1]}, "red": {"a": [0], "b": [0]}}}, "terms": ["blue", "missing"]}, {"document_ids": ["a"]}, sources=["index"])


def run(payload: dict):
    p = C.check(payload, SPEC)
    index = C.valid_index(p['index'])
    selected = set()
    for value in p['terms']:
        for term in C.terms(value): selected.update(index['postings'].get(term, {}))
    result = {'document_ids': [identifier for identifier in index['document_ids'] if identifier in selected]}
    return C.finish(result, SPEC)
