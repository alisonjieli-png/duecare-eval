"""Create overlapping token-count chunks while preserving original substrings and offsets; leading/trailing nontoken text is excluded."""
from . import _common as C

SPEC = C.spec("chunk_tokens", "Create overlapping token-count chunks while preserving original substrings and offsets; leading/trailing nontoken text is excluded.",
    {'text': C.S, 'size': C.integer(1), 'overlap': C.I}, {'chunks': C.arr(C.CHUNK)},
    {"text": "one, two three", "size": 2, "overlap": 1}, {"chunks": [{"id": "chunk-0", "start": 0, "end": 8, "text": "one, two"}, {"id": "chunk-1", "start": 5, "end": 14, "text": "two three"}]}, sources=["regex", "python"])


def run(payload: dict):
    p = C.check(payload, SPEC)
    C.require(p['overlap'] < p['size'], 'overlap must be smaller than size')
    words = C.tokens(p['text']); chunks = []; position = 0
    while position < len(words):
        last = min(len(words), position + p['size'])
        start, end = words[position]['start'], words[last - 1]['end']
        chunks.append({'id': 'chunk-' + str(len(chunks)), 'start': start, 'end': end, 'text': p['text'][start:end]})
        if last == len(words): break
        position += p['size'] - p['overlap']
    result = {'chunks': chunks}
    return C.finish(result, SPEC)
