"""Read CSV with a required unique, nonempty header and exact row widths; retain string values."""
from . import _shared as C

SPEC = C.spec("csv_records", "Read CSV with a required unique, nonempty header and exact row widths; retain string values.",
    {'text': C.S}, {'header': C.STRINGS, 'records': C.RECORDS, 'bom_removed': C.B},
    {"text": "a,b\n1,2\n"}, {"header": ["a", "b"], "records": [{"a": "1", "b": "2"}], "bom_removed": False}, [C.CSV_SOURCE])


def run(payload: dict) -> dict:
    p = C.check(payload, SPEC)
    rows, bom_removed = C.csv_rows(p['text'])
    C.require(bool(rows) and bool(rows[0]), 'csv_header_required')
    header = rows[0]
    C.require(all(header) and len(header) == len(set(header)), 'csv_duplicate_or_empty_header')
    result = {'header': header, 'records': [dict(zip(header, row)) for row in rows[1:]], 'bom_removed': bom_removed}
    return C.finish(result, SPEC)
