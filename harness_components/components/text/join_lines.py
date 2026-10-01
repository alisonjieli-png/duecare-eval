"""Join a supplied list without stripping or splitting its items."""
from ._shared import STRING, STRINGS, BOOLEAN, check, spec
SPEC = spec("join_lines", "Join supplied strings with a separator and optional final separator, including for an empty list.",
    {"lines": STRINGS, "separator": STRING, "final_separator": BOOLEAN}, {"text": STRING},
    {"lines": ["a", "b"]}, {"text": "a\nb"}, optional=("separator", "final_separator"))
def run(payload):
    p = check(payload, SPEC)
    separator = p.get("separator", "\n")
    return {"text": separator.join(p["lines"]) + (separator if p.get("final_separator", False) else "")}
