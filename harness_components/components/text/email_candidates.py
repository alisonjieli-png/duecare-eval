"""Locate whitespace-delimited tokens containing at signs."""
import re
from ._shared import STRING, INTEGER, EMAIL_OUTPUT, EMAIL_SOURCE, array, obj, check, email_record, spec
SPEC = spec("email_candidates", "Locate non-whitespace tokens containing @ and classify the complete token using the narrow mailbox parser; punctuation is not stripped and quoted/header syntax is unsupported.",
    {"text": STRING}, {"candidates": array(obj({"text": STRING, "start": INTEGER, "end": INTEGER, "mailbox": obj(EMAIL_OUTPUT)}))},
    {"text": "ask help@example.org"},
    {"candidates": [{"text": "help@example.org", "start": 4, "end": 20, "mailbox": {"status": "supported", "reason": "", "local": "help", "domain": "example.org", "normalized": "help@example.org"}}]},
    sources=(EMAIL_SOURCE,))
def run(payload):
    return {"candidates": [{"text": m.group(), "start": m.start(), "end": m.end(), "mailbox": email_record(m.group())} for m in re.finditer(r"\S+", check(payload, SPEC)["text"]) if "@" in m.group()]}
