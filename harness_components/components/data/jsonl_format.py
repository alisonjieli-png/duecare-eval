"""Serialize a list of JSON values as compact JSON lines with a final newline for every value."""
from . import _shared as C

SPEC = C.spec("jsonl_format", "Serialize a list of JSON values as compact JSON lines with a final newline for every value.",
    {'values': C.A}, {'text': C.S},
    {"values": [{"x": 1}, None]}, {"text": "{\"x\":1}\nnull\n"}, [C.JSON_SOURCE])


def run(payload: dict) -> dict:
    p = C.check(payload, SPEC)
    result = {'text': ''.join(C.compact(value) + '\n' for value in p['values'])}
    return C.finish(result, SPEC)
