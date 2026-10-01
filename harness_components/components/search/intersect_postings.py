"""Return documents containing all normalized supplied terms in original document order; empty terms return the document universe."""
from . import _common as C

SPEC = C.spec("intersect_postings", "Return documents containing all normalized supplied terms in original document order; empty terms return the document universe.",
    {'index': C.INDEX, 'terms': C.STRINGS}, {'document_ids': C.IDS},
    {"index": {"document_ids": ["a", "b"], "lengths": {"a": 2, "b": 1}, "postings": {"blue": {"a": [1]}, "red": {"a": [0], "b": [0]}}}, "terms": ["RED", "blue"]}, {"document_ids": ["a"]}, sources=["index"])


def run(payload: dict):
    p = C.check(payload, SPEC)
    index = C.valid_index(p['index'])
    wanted = {term for value in p['terms'] for term in C.terms(value)}
    selected = set(index['document_ids'])
    for term in wanted: selected.intersection_update(index['postings'].get(term, {}))
    result = {'document_ids': [identifier for identifier in index['document_ids'] if identifier in selected]}
    return C.finish(result, SPEC)
