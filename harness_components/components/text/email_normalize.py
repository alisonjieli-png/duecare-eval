"""Normalize a deliberately narrow mailbox syntax conservatively."""
from ._shared import STRING, EMAIL_OUTPUT, EMAIL_SOURCE, check, email_record, spec
SPEC = spec("email_normalize", "Normalize ASCII dot-atom mailboxes by lowercasing only the DNS domain; preserve local case, dots and plus tags. No whitespace trimming or delivery validation.",
    {"email": STRING}, EMAIL_OUTPUT,
    {"email": "Case+tag@EXAMPLE.ORG"}, {"status": "supported", "reason": "", "local": "Case+tag", "domain": "example.org", "normalized": "Case+tag@example.org"}, sources=(EMAIL_SOURCE,))
def run(payload):
    return email_record(check(payload, SPEC)["email"])
