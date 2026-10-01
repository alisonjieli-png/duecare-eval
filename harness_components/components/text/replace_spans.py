"""Apply nonoverlapping replacements against original offsets."""
from ._shared import STRING, INTEGER, array, obj, check, valid_spans, spec
_CHANGE = obj({"start": INTEGER, "end": INTEGER, "replacement": STRING})
SPEC = spec("replace_spans", "Apply replacements against original code-point offsets, sorted by start; reject overlaps and duplicate start offsets.",
    {"text": STRING, "replacements": array(_CHANGE)}, {"text": STRING, "replaced": INTEGER},
    {"text": "abcdef", "replacements": [{"start": 4, "end": 6, "replacement": "!"}, {"start": 1, "end": 3, "replacement": "X"}]},
    {"text": "aXd!", "replaced": 2})
def run(payload):
    p = check(payload, SPEC)
    changes = sorted(p["replacements"], key=lambda item: item["start"])
    valid_spans([[change["start"], change["end"]] for change in changes], len(p["text"]))
    result, end, previous_start = [], 0, -1
    for change in changes:
        start, stop = change["start"], change["end"]
        if start < end or start == previous_start:
            raise ValueError("replacements overlap or share a start offset")
        result.extend((p["text"][end:start], change["replacement"]))
        end, previous_start = stop, start
    result.append(p["text"][end:])
    return {"text": "".join(result), "replaced": len(changes)}
