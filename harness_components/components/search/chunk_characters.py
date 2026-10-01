"""Split text into exact character-offset chunks with caller-selected size and overlap; stop after the final covered character, with no redundant tail chunk."""
from . import _common as C

SPEC = C.spec("chunk_characters", "Split text into exact character-offset chunks with caller-selected size and overlap; stop after the final covered character, with no redundant tail chunk.",
    {'text': C.S, 'size': C.integer(1), 'overlap': C.I}, {'chunks': C.arr(C.CHUNK)},
    {"text": "abcdef", "size": 4, "overlap": 2}, {"chunks": [{"id": "chunk-0", "start": 0, "end": 4, "text": "abcd"}, {"id": "chunk-1", "start": 2, "end": 6, "text": "cdef"}]}, sources=["python"])


def run(payload: dict):
    p = C.check(payload, SPEC)
    C.require(p['overlap'] < p['size'], 'overlap must be smaller than size')
    chunks = []; start = 0
    while start < len(p['text']):
        end = min(len(p['text']), start + p['size'])
        chunks.append({'id': 'chunk-' + str(len(chunks)), 'start': start, 'end': end, 'text': p['text'][start:end]})
        if end == len(p['text']): break
        start += p['size'] - p['overlap']
    result = {'chunks': chunks}
    return C.finish(result, SPEC)
