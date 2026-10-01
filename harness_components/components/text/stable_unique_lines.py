"""Deduplicate exact lines in first occurrence order."""
from ._shared import STRING, STRINGS, INTEGER, check, spec
SPEC = spec("stable_unique_lines", "Deduplicate exact Unicode-split line bodies, preserving first occurrence order and blank lines.",
    {"text": STRING}, {"lines": STRINGS, "removed": INTEGER},
    {"text": "a\nb\na\n"}, {"lines": ["a", "b"], "removed": 1})
def run(payload):
    lines = check(payload, SPEC)["text"].splitlines()
    unique = list(dict.fromkeys(lines))
    return {"lines": unique, "removed": len(lines) - len(unique)}
