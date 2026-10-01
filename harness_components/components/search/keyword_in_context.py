"""Return a character-window concordance for each overlapping literal hit, separating original left, matched and right text."""
from . import _common as C

SPEC = C.spec("keyword_in_context", "Return a character-window concordance for each overlapping literal hit, separating original left, matched and right text.",
    {'text': C.S, 'needle': C.S, 'radius': C.I}, {'hits': C.arr(C.obj({'start': C.I, 'end': C.I, 'left': C.S, 'match': C.S, 'right': C.S}))},
    {"text": "a red b", "needle": "red", "radius": 2}, {"hits": [{"start": 2, "end": 5, "left": "a ", "match": "red", "right": " b"}]}, sources=["python"])


def run(payload: dict):
    p = C.check(payload, SPEC)
    hits = []
    for span in C.occurrences(p['text'], p['needle']):
        start, end = span['start'], span['end']
        hits.append({'start': start, 'end': end, 'left': p['text'][max(0, start - p['radius']):start], 'match': p['text'][start:end], 'right': p['text'][end:end + p['radius']]})
    result = {'hits': hits}
    return C.finish(result, SPEC)
