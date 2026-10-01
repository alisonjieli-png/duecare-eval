"""Mask the local part of a supported mailbox."""
from ._shared import STRING, integer, choice, EMAIL_SOURCE, check, email_parts, spec
SPEC = spec("email_mask", "Mask a supported ASCII mailbox local part with a constant marker, optionally revealing a prefix; domain remains visible and no anonymity guarantee is made.",
    {"email": STRING, "reveal_prefix": integer(), "marker": STRING},
    {"status": choice("supported", "invalid", "unsupported"), "reason": STRING, "masked": STRING},
    {"email": "Case+tag@EXAMPLE.ORG"}, {"status": "supported", "reason": "", "masked": "***@example.org"},
    optional=("reveal_prefix", "marker"), sources=(EMAIL_SOURCE,))
def run(payload):
    p = check(payload, SPEC)
    status, reason, local, domain = email_parts(p["email"])
    if status != "supported":
        return {"status": status, "reason": reason, "masked": ""}
    prefix = local[:p.get("reveal_prefix", 0)]
    marker = p.get("marker", "***")
    if not marker:
        raise ValueError("marker must not be empty")
    return {"status": status, "reason": "", "masked": prefix + marker + "@" + domain}
