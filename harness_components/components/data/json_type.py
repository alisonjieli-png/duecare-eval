"""Report the JSON/JSON-Schema type, distinguishing booleans, integers and noninteger number values."""
from . import _shared as C

SPEC = C.spec("json_type", "Report the JSON/JSON-Schema type, distinguishing booleans, integers and noninteger number values.",
    {'value': C.ANY}, {'type': C.S},
    {"value": True}, {"type": "boolean"}, [C.JSON_SOURCE])


def run(payload: dict) -> dict:
    p = C.check(payload, SPEC)
    names = {type(None): 'null', bool: 'boolean', int: 'integer', float: 'number', str: 'string', list: 'array', dict: 'object'}
    result = {'type': names[type(p['value'])]}
    return C.finish(result, SPEC)
