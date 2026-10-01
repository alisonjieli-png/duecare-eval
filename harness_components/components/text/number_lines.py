"""Number split lines without interpreting their contents."""
from ._shared import STRING, INTEGER, array, obj, check, spec
SPEC = spec("number_lines", "Return numbered Unicode-split lines; numbering may start at any integer.",
    {"text": STRING, "start": INTEGER}, {"lines": array(obj({"number": INTEGER, "text": STRING}))},
    {"text": "a\n\nb"}, {"lines": [{"number": 1, "text": "a"}, {"number": 2, "text": ""}, {"number": 3, "text": "b"}]},
    optional=("start",))
def run(payload):
    p = check(payload, SPEC)
    return {"lines": [{"number": i, "text": line} for i, line in enumerate(p["text"].splitlines(), p.get("start", 1))]}
