"""Build a parameterized UPDATE with nonempty assignments and explicit nonempty equality WHERE conditions; NULL conditions use IS NULL and no database is opened."""
from . import _common as C

SPEC = C.spec("build_update", "Build a parameterized UPDATE with nonempty assignments and explicit nonempty equality WHERE conditions; NULL conditions use IS NULL and no database is opened.",
    {'table': C.IDENTIFIER, 'values': C.mapping(C.SCALAR), 'where': C.mapping(C.SCALAR)}, C.SQL_OUTPUT,
    {"table": "docs", "values": {"text": "new"}, "where": {"id": 1}}, {"sql": "UPDATE \"docs\" SET \"text\" = ? WHERE \"id\" = ?", "params": ["new", 1]}, sources=["sqlite"])


def run(payload: dict):
    p = C.check(payload, SPEC)
    C.require(bool(p['values']), 'nonempty update values required')
    where, conditions = C.equal_where(p['where']); columns = sorted(p['values'])
    sql = 'UPDATE ' + C.quoted_identifier(p['table']) + ' SET ' + ', '.join(C.quoted_identifier(column) + ' = ?' for column in columns) + ' WHERE ' + where
    result = {'sql': sql, 'params': [p['values'][column] for column in columns] + conditions}
    return C.finish(result, SPEC)
