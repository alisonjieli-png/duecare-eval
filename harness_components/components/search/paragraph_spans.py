"""Locate nonblank paragraph runs with original offsets and line endings intact; blank lines delimit paragraphs without rewriting their contents."""
from . import _common as C

SPEC = C.spec("paragraph_spans", "Locate nonblank paragraph runs with original offsets and line endings intact; blank lines delimit paragraphs without rewriting their contents.",
    {'text': C.S}, {'paragraphs': C.arr(C.CHUNK)},
    {"text": "a\r\nb\r\n\r\nc"}, {"paragraphs": [{"id": "paragraph-0", "start": 0, "end": 4, "text": "a\r\nb"}, {"id": "paragraph-1", "start": 8, "end": 9, "text": "c"}]}, sources=["python"])


def run(payload: dict):
    p = C.check(payload, SPEC)
    paragraphs = []; start = None; end = None
    for line in C.lines(p['text']):
        if line['text'].strip():
            if start is None: start = line['start']
            end = line['end']
        elif start is not None:
            paragraphs.append({'id': 'paragraph-' + str(len(paragraphs)), 'start': start, 'end': end, 'text': p['text'][start:end]})
            start = None
    if start is not None: paragraphs.append({'id': 'paragraph-' + str(len(paragraphs)), 'start': start, 'end': end, 'text': p['text'][start:end]})
    result = {'paragraphs': paragraphs}
    return C.finish(result, SPEC)
