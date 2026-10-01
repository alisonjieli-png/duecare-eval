"""Build a parameterized membership predicate; empty values give false, NULL adds IS NULL, and repeated non-NULL values retain their exact bindings."""
from . import _common as C

SPEC = C.spec("build_in_clause", "Build a parameterized membership predicate; empty values give false, NULL adds IS NULL, and repeated non-NULL values retain their exact bindings.",
    {'column': C.IDENTIFIER, 'values': C.arr(C.SCALAR)}, C.SQL_OUTPUT,
    {"column": "id", "values": [1, None, 2]}, {"sql": "(\"id\" IN (?, ?) OR \"id\" IS NULL)", "params": [1, 2]}, sources=["sqlite", "like"])


def run(payload: dict):
    p = C.check(payload, SPEC)
    column = C.quoted_identifier(p['column']); values = [value for value in p['values'] if value is not None]; clauses = []
    if values: clauses.append(column + ' IN (' + ', '.join('?' for _ in values) + ')')
    if None in p['values']: clauses.append(column + ' IS NULL')
    sql = '(' + ' OR '.join(clauses) + ')' if len(clauses) > 1 else clauses[0] if clauses else '0'
    result = {'sql': sql, 'params': values}
    return C.finish(result, SPEC)
