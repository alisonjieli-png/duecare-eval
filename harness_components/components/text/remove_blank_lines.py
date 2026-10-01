"""Remove lines whose body is Unicode whitespace or empty."""
from ._shared import STRING, INTEGER, check, spec
SPEC = spec("remove_blank_lines", "Remove whitespace-only lines, retaining each surviving original line ending.",
    {"text": STRING}, {"text": STRING, "removed": INTEGER},
    {"text": "a\n \n\nb"}, {"text": "a\nb", "removed": 2})
def run(payload):
    lines = check(payload, SPEC)["text"].splitlines(keepends=True)
    kept = [line for line in lines if line.strip()]
    return {"text": "".join(kept), "removed": len(lines) - len(kept)}
