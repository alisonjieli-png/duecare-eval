"""Find contiguous normalized token phrases with original Unicode offsets; punctuation between tokens is ignored, and an empty phrase has no matches."""
from . import _common as C

SPEC = C.spec("match_phrase", "Find contiguous normalized token phrases with original Unicode offsets; punctuation between tokens is ignored, and an empty phrase has no matches.",
    {'text': C.S, 'phrase': C.S}, {'matches': C.arr(C.SPAN)},
    {"text": "red, blue red blue", "phrase": "RED blue"}, {"matches": [{"start": 0, "end": 9}, {"start": 10, "end": 18}]}, sources=["index", "regex"])


def run(payload: dict):
    p = C.check(payload, SPEC)
    result = {'matches': C.phrase_spans(p['text'], p['phrase'])}
    return C.finish(result, SPEC)
