"""Build a complete in-memory positional index with token counts and document IDs; duplicate document IDs are rejected."""
from . import _common as C

SPEC = C.spec("build_inverted_index", "Build a complete in-memory positional index with token counts and document IDs; duplicate document IDs are rejected.",
    {'documents': C.DOCS}, {'index': C.INDEX},
    {"documents": [{"id": "a", "text": "Red blue"}, {"id": "b", "text": "red"}]}, {"index": {"document_ids": ["a", "b"], "lengths": {"a": 2, "b": 1}, "postings": {"blue": {"a": [1]}, "red": {"a": [0], "b": [0]}}}}, sources=["index"])


def run(payload: dict):
    p = C.check(payload, SPEC)
    result = {'index': C.index_documents(p['documents'])}
    return C.finish(result, SPEC)
