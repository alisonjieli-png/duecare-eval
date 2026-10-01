"""Pack whole passages in supplied priority order under a caller's Unicode-character budget, using separate citation offsets and explicit omitted IDs; no passage is silently truncated."""
from . import _common as C

SPEC = C.spec("assemble_context", "Pack whole passages in supplied priority order under a caller's Unicode-character budget, using separate citation offsets and explicit omitted IDs; no passage is silently truncated.",
    {'passages': C.DOCS, 'max_characters': C.I}, {'text': C.S, 'included_ids': C.IDS, 'omitted_ids': C.IDS, 'citations': C.arr(C.obj({'id': C.S, 'start': C.I, 'end': C.I}))},
    {"passages": [{"id": "a", "text": "red"}, {"id": "b", "text": "blue"}], "max_characters": 7}, {"text": "red", "included_ids": ["a"], "omitted_ids": ["b"], "citations": [{"id": "a", "start": 0, "end": 3}]}, sources=["python"])


def run(payload: dict):
    p = C.check(payload, SPEC)
    rows = C.documents(p['passages']); text = ''; included = []; omitted = []; citations = []
    for row in rows:
        separator = '\n\n' if included else ''
        if len(text) + len(separator) + len(row['text']) > p['max_characters']:
            omitted.append(row['id']); continue
        start = len(text) + len(separator)
        text += separator + row['text']; included.append(row['id'])
        citations.append({'id': row['id'], 'start': start, 'end': len(text)})
    result = {'text': text, 'included_ids': included, 'omitted_ids': omitted, 'citations': citations}
    return C.finish(result, SPEC)
