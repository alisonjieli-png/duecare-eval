"""Parse nonempty JSON lines; blank lines are refused and one final newline is accepted."""
from . import _shared as C

SPEC = C.spec("jsonl_parse", "Parse nonempty JSON lines; blank lines are refused and one final newline is accepted.",
    {'text': C.S}, {'values': C.A},
    {"text": "{\"x\":1}\nnull\n"}, {"values": [{"x": 1}, None]}, [C.JSON_SOURCE])


def run(payload: dict) -> dict:
    p = C.check(payload, SPEC)
    lines = p['text'].split('\n')
    if lines and lines[-1] == '':
        lines.pop()
    C.require(all(line.strip() for line in lines), 'blank_jsonl_line')
    result = {'values': [C.parse_json(line) for line in lines]}
    return C.finish(result, SPEC)
