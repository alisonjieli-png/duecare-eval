"""Merge touching line-context windows around literal hits, retaining exact original text, offsets and matched line numbers."""
from . import _common as C

SPEC = C.spec("grep_context", "Merge touching line-context windows around literal hits, retaining exact original text, offsets and matched line numbers.",
    {'text': C.S, 'needle': C.S, 'before': C.I, 'after': C.I}, {'contexts': C.arr(C.obj({'start_line': C.integer(1), 'end_line': C.integer(1), 'start': C.I, 'end': C.I, 'text': C.S, 'matched_lines': C.arr(C.integer(1))}))},
    {"text": "a\nred\nb", "needle": "red", "before": 1, "after": 1}, {"contexts": [{"start_line": 1, "end_line": 3, "start": 0, "end": 7, "text": "a\nred\nb", "matched_lines": [2]}]}, sources=["python"])


def run(payload: dict):
    p = C.check(payload, SPEC)
    rows = C.lines(p['text'])
    hits = [i for i, row in enumerate(rows) if p['needle'] and p['needle'] in row['text']]
    windows = C.merge_intervals([[max(0, i - p['before']), min(len(rows), i + p['after'] + 1)] for i in hits])
    contexts = []
    for first, last in windows:
        start, end = rows[first]['start'], rows[last - 1]['end']
        contexts.append({'start_line': first + 1, 'end_line': last, 'start': start, 'end': end, 'text': p['text'][start:end], 'matched_lines': [i + 1 for i in hits if first <= i < last]})
    result = {'contexts': contexts}
    return C.finish(result, SPEC)
