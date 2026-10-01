"""Find consecutive token positions for a normalized phrase directly in a validated positional index; repeated terms and overlapping phrases are supported."""
from . import _common as C

SPEC = C.spec("positional_phrase", "Find consecutive token positions for a normalized phrase directly in a validated positional index; repeated terms and overlapping phrases are supported.",
    {'index': C.INDEX, 'phrase': C.S}, {'matches': C.arr(C.obj({'id': C.S, 'positions': C.arr(C.I)}))},
    {"index": {"document_ids": ["a", "b"], "lengths": {"a": 2, "b": 1}, "postings": {"blue": {"a": [1]}, "red": {"a": [0], "b": [0]}}}, "phrase": "RED blue"}, {"matches": [{"id": "a", "positions": [0]}]}, sources=["index"])


def run(payload: dict):
    p = C.check(payload, SPEC)
    index = C.valid_index(p['index']); wanted = C.terms(p['phrase']); matches = []
    if wanted:
        for identifier in index['document_ids']:
            starts = index['postings'].get(wanted[0], {}).get(identifier, [])
            valid = [start for start in starts if all(start + offset in index['postings'].get(term, {}).get(identifier, []) for offset, term in enumerate(wanted))]
            if valid: matches.append({'id': identifier, 'positions': valid})
    result = {'matches': matches}
    return C.finish(result, SPEC)
