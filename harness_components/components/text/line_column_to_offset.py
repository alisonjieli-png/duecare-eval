"""Convert LF line/column coordinates into a code-point offset."""
from ._shared import STRING, INTEGER, integer, check, spec
SPEC = spec("line_column_to_offset", "Map a one-based LF line and zero-based code-point column to an offset; end-of-line columns are allowed.",
    {"text": STRING, "line": integer(1), "column": integer()}, {"offset": INTEGER},
    {"text": "ab\nc", "line": 2, "column": 1}, {"offset": 4})
def run(payload):
    p = check(payload, SPEC)
    lines = p["text"].split("\n")
    if p["line"] > len(lines) or p["column"] > len(lines[p["line"] - 1]):
        raise ValueError("line or column exceeds text bounds")
    return {"offset": sum(len(line) + 1 for line in lines[:p["line"] - 1]) + p["column"]}
