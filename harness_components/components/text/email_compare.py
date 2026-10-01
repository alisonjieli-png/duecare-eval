"""Compare two supported mailboxes conservatively."""
from ._shared import STRING, BOOLEAN, EMAIL_OUTPUT, EMAIL_SOURCE, obj, check, email_record, spec
SPEC = spec("email_compare", "Compare supported ASCII mailbox forms using domain-only case normalization; preserve distinctions that depend on provider-specific mailbox rules.",
    {"left": STRING, "right": STRING}, {"comparable": BOOLEAN, "equal": BOOLEAN, "left": obj(EMAIL_OUTPUT), "right": obj(EMAIL_OUTPUT)},
    {"left": "A@EXAMPLE.ORG", "right": "a@example.org"},
    {"comparable": True, "equal": False, "left": {"status": "supported", "reason": "", "local": "A", "domain": "example.org", "normalized": "A@example.org"}, "right": {"status": "supported", "reason": "", "local": "a", "domain": "example.org", "normalized": "a@example.org"}},
    sources=(EMAIL_SOURCE,))
def run(payload):
    p = check(payload, SPEC)
    left, right = email_record(p["left"]), email_record(p["right"])
    comparable = left["status"] == right["status"] == "supported"
    return {"comparable": comparable, "equal": comparable and left["normalized"] == right["normalized"], "left": left, "right": right}
