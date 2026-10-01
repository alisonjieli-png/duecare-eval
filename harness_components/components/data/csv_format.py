"""Format equal-width string rows with comma delimiters, CSV quoting and CRLF endings; do not change cell values."""
from . import _shared as C

SPEC = C.spec("csv_format", "Format equal-width string rows with comma delimiters, CSV quoting and CRLF endings; do not change cell values.",
    {'rows': C.ROWS}, {'text': C.S},
    {"rows": [["a", "b"], ["1", "x,y"]]}, {"text": "a,b\r\n1,\"x,y\"\r\n"}, [C.CSV_SOURCE])


def run(payload: dict) -> dict:
    p = C.check(payload, SPEC)
    result = {'text': C.csv_text(p['rows'])}
    return C.finish(result, SPEC)
