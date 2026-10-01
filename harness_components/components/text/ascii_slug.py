"""Create an explicitly lossy ASCII slug, without identity claims."""
import re
import unicodedata
from ._shared import STRING, check, spec, UNICODE_SOURCE
SPEC = spec("ascii_slug", "NFKD-decompose and discard non-ASCII characters, then join lowercase ASCII alphanumeric runs with hyphens; collisions are possible.",
    {"text": STRING}, {"slug": STRING}, {"text": "Café / Notes"}, {"slug": "cafe-notes"}, sources=(UNICODE_SOURCE,))
SPEC["unicode_database"] = unicodedata.unidata_version
def run(payload):
    text = unicodedata.normalize("NFKD", check(payload, SPEC)["text"]).encode("ascii", "ignore").decode("ascii").lower()
    return {"slug": "-".join(re.findall(r"[a-z0-9]+", text))}
