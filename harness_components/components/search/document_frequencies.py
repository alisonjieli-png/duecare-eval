"""Count distinct indexed documents per term and return collection size, preserving zero-document collections."""
from . import _common as C

SPEC = C.spec("document_frequencies", "Count distinct indexed documents per term and return collection size, preserving zero-document collections.",
    {'index': C.INDEX}, {'document_count': C.I, 'frequencies': C.mapping(C.I)},
    {"index": {"document_ids": ["a", "b"], "lengths": {"a": 2, "b": 1}, "postings": {"blue": {"a": [1]}, "red": {"a": [0], "b": [0]}}}}, {"document_count": 2, "frequencies": {"blue": 1, "red": 2}}, sources=["tfidf", "index"])


def run(payload: dict):
    p = C.check(payload, SPEC)
    index = C.valid_index(p['index'])
    result = {'document_count': len(index['document_ids']), 'frequencies': {term: len(posting) for term, posting in index['postings'].items()}}
    return C.finish(result, SPEC)
