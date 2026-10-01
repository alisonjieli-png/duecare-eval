"""Prefix nonblank lines or every line."""
import textwrap
from ._shared import STRING, BOOLEAN, check, spec
SPEC = spec("indent_text", "Prefix each nonblank line, or include blank lines when requested.",
    {"text": STRING, "prefix": STRING, "include_blank": BOOLEAN}, {"text": STRING},
    {"text": "a\n\nb", "prefix": "> "}, {"text": "> a\n\n> b"}, optional=("include_blank",))
def run(payload):
    p = check(payload, SPEC)
    predicate = (lambda line: True) if p.get("include_blank", False) else None
    return {"text": textwrap.indent(p["text"], p["prefix"], predicate)}
