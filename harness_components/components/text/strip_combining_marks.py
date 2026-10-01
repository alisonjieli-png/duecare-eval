"""Explicitly lossy decomposition and combining-mark removal."""
import unicodedata
from ._shared import STRING, INTEGER, check, spec, UNICODE_SOURCE
SPEC = spec("strip_combining_marks", "NFD-decompose, remove all Unicode M-category code points, then NFC-compose; explicitly lossy and not transliteration.",
    {"text": STRING}, {"text": STRING, "removed_marks": INTEGER},
    {"text": "café"}, {"text": "cafe", "removed_marks": 1}, sources=(UNICODE_SOURCE,))
SPEC["unicode_database"] = unicodedata.unidata_version
def run(payload):
    text = unicodedata.normalize("NFD", check(payload, SPEC)["text"])
    kept = [char for char in text if not unicodedata.category(char).startswith("M")]
    return {"text": unicodedata.normalize("NFC", "".join(kept)), "removed_marks": len(text) - len(kept)}
