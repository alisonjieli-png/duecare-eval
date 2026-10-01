"""Group supported mailboxes without conflating local parts."""
from ._shared import STRING, STRINGS, INTEGER, EMAIL_SOURCE, array, obj, choice, check, email_parts, spec
SPEC = spec("email_group_by_domain", "Group supported mailboxes by lowercase domain in first-seen order; preserve duplicates and return every invalid/unsupported input index.",
    {"emails": STRINGS},
    {"groups": array(obj({"domain": STRING, "emails": STRINGS})), "rejected": array(obj({"index": INTEGER, "status": choice("invalid", "unsupported"), "reason": STRING}))},
    {"emails": ["A@EXAMPLE.ORG", "B@example.org", "bad"]},
    {"groups": [{"domain": "example.org", "emails": ["A@example.org", "B@example.org"]}], "rejected": [{"index": 2, "status": "invalid", "reason": "expected_one_at_sign"}]},
    sources=(EMAIL_SOURCE,))
def run(payload):
    grouped, rejected = {}, []
    for index, value in enumerate(check(payload, SPEC)["emails"]):
        status, reason, local, domain = email_parts(value)
        if status == "supported":
            grouped.setdefault(domain, []).append(local + "@" + domain)
        else:
            rejected.append({"index": index, "status": status, "reason": reason})
    return {"groups": [{"domain": domain, "emails": emails} for domain, emails in grouped.items()], "rejected": rejected}
