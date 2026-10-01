"""Parse JSON, rejecting duplicate keys, nonfinite numbers and unpaired Unicode surrogates."""
from . import _shared as C

SPEC = C.spec("json_parse", "Parse JSON, rejecting duplicate keys, nonfinite numbers and unpaired Unicode surrogates.",
    {'text': C.S}, {'value': C.ANY},
    {"text": "{\"x\":[1,true]}"}, {"value": {"x": [1, True]}}, [C.JSON_SOURCE])


def run(payload: dict) -> dict:
    p = C.check(payload, SPEC)
    result = {'value': C.parse_json(p['text'])}
    return C.finish(result, SPEC)
