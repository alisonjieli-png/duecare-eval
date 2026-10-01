"""Apply one Unicode normalization form without silent case changes."""
import unicodedata
from ._shared import STRING, BOOLEAN, choice, check, spec, UNICODE_SOURCE
SPEC = spec("unicode_normalize", "Apply NFC, NFD, NFKC or NFKD normalization; compatibility forms may change visual distinctions.",
    {"text": STRING, "form": choice("NFC", "NFD", "NFKC", "NFKD")}, {"text": STRING, "changed": BOOLEAN},
    {"text": "e\u0301", "form": "NFC"}, {"text": "é", "changed": True}, sources=(UNICODE_SOURCE,))
SPEC["unicode_database"] = unicodedata.unidata_version
def run(payload):
    p = check(payload, SPEC)
    normalized = unicodedata.normalize(p["form"], p["text"])
    return {"text": normalized, "changed": normalized != p["text"]}
