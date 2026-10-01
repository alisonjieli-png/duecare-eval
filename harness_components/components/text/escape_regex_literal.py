"""Escape text for insertion into a Python regex pattern."""
import re
from ._shared import STRING, check, spec, REGEX_SOURCE
SPEC = spec("escape_regex_literal", "Escape a literal for Python regular-expression patterns; do not use this as replacement-string escaping.",
    {"text": STRING}, {"pattern": STRING}, {"text": "a+b"}, {"pattern": "a\\+b"}, sources=(REGEX_SOURCE,))
def run(payload):
    return {"pattern": re.escape(check(payload, SPEC)["text"])}
