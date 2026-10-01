"""Parse comma-separated string rows with strict quoting and equal widths; remove and report one leading BOM."""
from . import _shared as C

SPEC = C.spec("csv_parse", "Parse comma-separated string rows with strict quoting and equal widths; remove and report one leading BOM.",
    {'text': C.S}, {'rows': C.ROWS, 'bom_removed': C.B},
    {"text": "﻿a,b\r\n1,\"x,y\"\r\n"}, {"rows": [["a", "b"], ["1", "x,y"]], "bom_removed": True}, [C.CSV_SOURCE])


def run(payload: dict) -> dict:
    p = C.check(payload, SPEC)
    rows, bom_removed = C.csv_rows(p['text'])
    result = {'rows': rows, 'bom_removed': bom_removed}
    return C.finish(result, SPEC)
