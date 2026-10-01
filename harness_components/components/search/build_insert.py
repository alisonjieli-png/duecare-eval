"""Build a parameterized INSERT with lexicographically ordered columns; an empty record produces DEFAULT VALUES, and this function executes nothing."""
from . import _common as C

SPEC = C.spec("build_insert", "Build a parameterized INSERT with lexicographically ordered columns; an empty record produces DEFAULT VALUES, and this function executes nothing.",
    {'table': C.IDENTIFIER, 'record': C.mapping(C.SCALAR)}, C.SQL_OUTPUT,
    {"table": "docs", "record": {"text": "x'; DROP TABLE docs;--", "id": 1}}, {"sql": "INSERT INTO \"docs\" (\"id\", \"text\") VALUES (?, ?)", "params": [1, "x'; DROP TABLE docs;--"]}, sources=["sqlite"])


def run(payload: dict):
    p = C.check(payload, SPEC)
    columns = sorted(p['record']); table = C.quoted_identifier(p['table'])
    if columns:
        sql = 'INSERT INTO ' + table + ' (' + ', '.join(C.quoted_identifier(column) for column in columns) + ') VALUES (' + ', '.join('?' for _ in columns) + ')'
    else: sql = 'INSERT INTO ' + table + ' DEFAULT VALUES'
    result = {'sql': sql, 'params': [p['record'][column] for column in columns]}
    return C.finish(result, SPEC)
