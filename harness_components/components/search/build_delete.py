"""Build a parameterized DELETE statement requiring explicit nonempty equality conditions; return SQL and bindings without executing effects."""
from . import _common as C

SPEC = C.spec("build_delete", "Build a parameterized DELETE statement requiring explicit nonempty equality conditions; return SQL and bindings without executing effects.",
    {'table': C.IDENTIFIER, 'where': C.mapping(C.SCALAR)}, C.SQL_OUTPUT,
    {"table": "docs", "where": {"id": 1}}, {"sql": "DELETE FROM \"docs\" WHERE \"id\" = ?", "params": [1]}, sources=["sqlite"])


def run(payload: dict):
    p = C.check(payload, SPEC)
    where, params = C.equal_where(p['where'])
    result = {'sql': 'DELETE FROM ' + C.quoted_identifier(p['table']) + ' WHERE ' + where, 'params': params}
    return C.finish(result, SPEC)
