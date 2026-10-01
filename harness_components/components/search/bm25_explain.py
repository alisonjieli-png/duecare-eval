"""Explain the BM25 score for one identified document, including corpus average length, df, tf, positive IDF and each query-term contribution."""
from . import _common as C

SPEC = C.spec("bm25_explain", "Explain the BM25 score for one identified document, including corpus average length, df, tf, positive IDF and each query-term contribution.",
    {'documents': C.DOCS, 'document_id': C.S, 'query': C.S, 'k1': C.number(0), 'b': C.number(0, 1)}, {'document_id': C.S, 'average_document_length': C.N, 'score': C.N, 'terms': C.arr(C.obj({'term': C.S, 'document_frequency': C.I, 'term_frequency': C.I, 'idf': C.N, 'length_normalization': C.N, 'contribution': C.N}))},
    {"documents": [{"id": "a", "text": "red"}], "document_id": "a", "query": "red", "k1": 1.2, "b": 0.75}, {"document_id": "a", "average_document_length": 1, "score": 0.287682072452, "terms": [{"term": "red", "document_frequency": 1, "term_frequency": 1, "idf": 0.287682072452, "length_normalization": 1, "contribution": 0.287682072452}]}, sources=["bm25"])


def run(payload: dict):
    p = C.check(payload, SPEC)
    parts, average = C.bm25_parts(p['documents'], p['query'], p['k1'], p['b'])
    C.require(p['document_id'] in parts, 'unknown document ID')
    components = parts[p['document_id']]
    score = C.math.fsum(term['contribution'] for term in components)
    rounded = [{key: round(value, 12) if type(value) is float else value for key, value in term.items()} for term in components]
    result = {'document_id': p['document_id'], 'average_document_length': round(average, 12), 'score': round(score, 12), 'terms': rounded}
    return C.finish(result, SPEC)
