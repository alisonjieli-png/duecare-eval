"""Escape literal SQL LIKE percent, underscore and escape characters; return a pattern value for parameter binding with a one-character ESCAPE other than percent or underscore."""
from . import _common as C

SPEC = C.spec("escape_like", "Escape literal SQL LIKE percent, underscore and escape characters; return a pattern value for parameter binding with a one-character ESCAPE other than percent or underscore.",
    {'value': C.S, 'escape': C.S}, {'pattern': C.S, 'escape': C.S},
    {"value": "50%_off\\x", "escape": "\\"}, {"pattern": "50\\%\\_off\\\\x", "escape": "\\"}, sources=["like"])


def run(payload: dict):
    p = C.check(payload, SPEC)
    escape = p['escape']
    C.require(len(escape) == 1 and escape not in '%_\x00', 'one non-wildcard non-NUL escape character required')
    C.require('\x00' not in p['value'], 'SQLite LIKE literal must not contain NUL')
    pattern = p['value'].replace(escape, escape + escape).replace('%', escape + '%').replace('_', escape + '_')
    result = {'pattern': pattern, 'escape': escape}
    return C.finish(result, SPEC)
