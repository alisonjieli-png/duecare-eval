"""Serialize finite JSON values with two-space indentation and preserved object insertion order."""
from . import _shared as C
import json

SPEC = C.spec("json_pretty", "Serialize finite JSON values with two-space indentation and preserved object insertion order.",
    {'value': C.ANY}, {'text': C.S},
    {"value": {"x": 1}}, {"text": "{\n  \"x\": 1\n}"}, [C.JSON_SOURCE])


def run(payload: dict) -> dict:
    p = C.check(payload, SPEC)
    result = {'text': json.dumps(p['value'], ensure_ascii=False, allow_nan=False, indent=2)}
    return C.finish(result, SPEC)
