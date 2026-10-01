"""Convert a code-point offset to LF line/column coordinates."""
from bisect import bisect_right
from ._shared import STRING, INTEGER, integer, check, spec
SPEC = spec("offset_to_line_column", "Map an offset in [0,len(text)] to one-based LF line and zero-based code-point column; LF belongs to the preceding line.",
    {"text": STRING, "offset": integer()}, {"line": INTEGER, "column": INTEGER},
    {"text": "ab\nc", "offset": 3}, {"line": 2, "column": 0})
def run(payload):
    p = check(payload, SPEC)
    if p["offset"] > len(p["text"]):
        raise ValueError("offset exceeds text length")
    starts = [0] + [i + 1 for i, char in enumerate(p["text"]) if char == "\n"]
    line = bisect_right(starts, p["offset"]) - 1
    return {"line": line + 1, "column": p["offset"] - starts[line]}
