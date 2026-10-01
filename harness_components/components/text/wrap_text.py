"""Wrap text by code-point widths using stdlib textwrap."""
import textwrap
from ._shared import STRING, STRINGS, BOOLEAN, integer, check, spec
SPEC = spec("wrap_text", "Wrap with stdlib textwrap, collapsing whitespace; width is code-point based, not terminal display width.",
    {"text": STRING, "width": integer(1), "break_long_words": BOOLEAN, "break_on_hyphens": BOOLEAN}, {"lines": STRINGS},
    {"text": "one two three", "width": 7}, {"lines": ["one two", "three"]}, optional=("break_long_words", "break_on_hyphens"),
    sources=("https://docs.python.org/3/library/textwrap.html",))
def run(payload):
    p = check(payload, SPEC)
    return {"lines": textwrap.wrap(p["text"], width=p["width"], break_long_words=p.get("break_long_words", True), break_on_hyphens=p.get("break_on_hyphens", True))}
