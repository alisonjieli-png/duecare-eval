"""Rank by BM25 with Lucene positive IDF log(1+(N-df+0.5)/(df+0.5)); use unique query terms, k1>0 and b in [0,1], ID tie breaks and 12-decimal reported scores."""
from . import _common as C

SPEC = C.spec("bm25_rank", "Rank by BM25 with Lucene positive IDF log(1+(N-df+0.5)/(df+0.5)); use unique query terms, k1>0 and b in [0,1], ID tie breaks and 12-decimal reported scores.",
    {'documents': C.DOCS, 'query': C.S, 'k1': C.number(0), 'b': C.number(0, 1), 'limit': C.I}, {'results': C.RANKING},
    {"documents": [{"id": "a", "text": "red"}], "query": "red", "k1": 1.2, "b": 0.75, "limit": 1}, {"results": [{"id": "a", "score": 0.287682072452, "rank": 1}]}, sources=["bm25"])


def run(payload: dict):
    p = C.check(payload, SPEC)
    parts, average = C.bm25_parts(p['documents'], p['query'], p['k1'], p['b'])
    scores = {identifier: C.math.fsum(term['contribution'] for term in components) for identifier, components in parts.items()}
    result = {'results': C.ranking(scores, p['limit'])}
    return C.finish(result, SPEC)
