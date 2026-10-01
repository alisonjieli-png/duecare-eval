"""Split all Python-recognized Unicode line boundaries."""
from ._shared import STRING, STRINGS, BOOLEAN, check, spec
SPEC = spec("split_lines", "Split Unicode line boundaries using str.splitlines; a terminal separator adds no empty line.",
    {"text": STRING, "keepends": BOOLEAN}, {"lines": STRINGS},
    {"text": "a\r\nb\u2028c\n"}, {"lines": ["a", "b", "c"]}, optional=("keepends",))
def run(payload):
    p = check(payload, SPEC)
    return {"lines": p["text"].splitlines(p.get("keepends", False))}
