"""Report zero-based cells beginning with common spreadsheet formula or control prefixes after ASCII spaces; leave cells unchanged."""
from . import _shared as C

SPEC = C.spec("csv_formula_flags", "Report zero-based cells beginning with common spreadsheet formula or control prefixes after ASCII spaces; leave cells unchanged.",
    {'rows': C.ROWS}, {'flags': C.A},
    {"rows": [["safe", "  =1+1"], ["@SUM(A1)", "\ttext"]]}, {"flags": [{"row": 0, "column": 1, "prefix": "="}, {"row": 1, "column": 0, "prefix": "@"}, {"row": 1, "column": 1, "prefix": "\t"}]}, [C.CSV_SOURCE, 'https://owasp.org/www-community/attacks/CSV_Injection'])


def run(payload: dict) -> dict:
    p = C.check(payload, SPEC)
    flags = []
    for row_index, row in enumerate(p['rows']):
        for column, cell in enumerate(row):
            prefix = cell.lstrip(' ')[:1]
            if prefix and prefix in '=+-@\t\r\n＝＋－＠':
                flags.append({'row': row_index, 'column': column, 'prefix': prefix})
    result = {'flags': flags}
    return C.finish(result, SPEC)
