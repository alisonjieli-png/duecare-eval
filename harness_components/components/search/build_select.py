"""Build a parameterized SELECT with explicit columns, comparison/LIKE filters, ordered sorting and bound LIMIT/OFFSET; NULL equality becomes IS NULL and no SQL is executed."""
from . import _common as C

SPEC = C.spec("build_select", "Build a parameterized SELECT with explicit columns, comparison/LIKE filters, ordered sorting and bound LIMIT/OFFSET; NULL equality becomes IS NULL and no SQL is executed.",
    {'table': C.IDENTIFIER, 'columns': C.arr(C.IDENTIFIER, 1, True), 'filters': C.arr(C.obj({'column': C.IDENTIFIER, 'operator': C.choice('=', '!=', '<', '<=', '>', '>=', 'LIKE'), 'value': C.SCALAR})), 'order_by': C.arr(C.obj({'column': C.IDENTIFIER, 'direction': C.choice('ASC', 'DESC')})), 'limit': C.I, 'offset': C.I}, C.SQL_OUTPUT,
    {"table": "docs", "columns": ["id", "text"], "filters": [{"column": "id", "operator": "=", "value": 2}], "order_by": [{"column": "id", "direction": "DESC"}], "limit": 10, "offset": 0}, {"sql": "SELECT \"id\", \"text\" FROM \"docs\" WHERE \"id\" = ? ORDER BY \"id\" DESC LIMIT ? OFFSET ?", "params": [2, 10, 0]}, sources=["sqlite"])


def run(payload: dict):
    p = C.check(payload, SPEC)
    params = []; clauses = []
    for condition in p['filters']:
        column, operator, value = C.quoted_identifier(condition['column']), condition['operator'], condition['value']
        if value is None:
            C.require(operator in ('=', '!='), 'NULL supports only equality and inequality filters')
            clauses.append(column + (' IS NULL' if operator == '=' else ' IS NOT NULL'))
        else:
            C.require(operator != 'LIKE' or type(value) is str, 'LIKE pattern must be text')
            clauses.append(column + ' ' + operator + ' ?'); params.append(value)
    sql = 'SELECT ' + ', '.join(C.quoted_identifier(column) for column in p['columns']) + ' FROM ' + C.quoted_identifier(p['table'])
    if clauses: sql += ' WHERE ' + ' AND '.join(clauses)
    C.require(len({order['column'] for order in p['order_by']}) == len(p['order_by']), 'duplicate ORDER BY column')
    if p['order_by']: sql += ' ORDER BY ' + ', '.join(C.quoted_identifier(order['column']) + ' ' + order['direction'] for order in p['order_by'])
    sql += ' LIMIT ? OFFSET ?'; params.extend([p['limit'], p['offset']])
    result = {'sql': sql, 'params': params}
    return C.finish(result, SPEC)
