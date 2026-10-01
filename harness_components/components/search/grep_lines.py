"""Select lines containing a case-sensitive literal and return original line numbers, offsets and text; an empty needle returns no lines."""
from . import _common as C

SPEC = C.spec("grep_lines", "Select lines containing a case-sensitive literal and return original line numbers, offsets and text; an empty needle returns no lines.",
    {'text': C.S, 'needle': C.S}, {'lines': C.arr(C.obj({'line': C.integer(1), 'start': C.I, 'end': C.I, 'text': C.S}))},
    {"text": "a\nred\nb", "needle": "red"}, {"lines": [{"line": 2, "start": 2, "end": 5, "text": "red"}]}, sources=["python"])


def run(payload: dict):
    p = C.check(payload, SPEC)
    result = {'lines': [line for line in C.lines(p['text']) if p['needle'] and p['needle'] in line['text']]}
    return C.finish(result, SPEC)
