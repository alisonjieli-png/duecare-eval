"""Remove common leading whitespace using textwrap.dedent."""
import textwrap
from ._shared import STRING, check, spec
SPEC = spec("dedent_text", "Remove common leading indentation; tabs and spaces remain distinct.",
    {"text": STRING}, {"text": STRING},
    {"text": "  a\n    b\n"}, {"text": "a\n  b\n"},
    sources=("https://docs.python.org/3/library/textwrap.html",))
def run(payload):
    return {"text": textwrap.dedent(check(payload, SPEC)["text"])}
