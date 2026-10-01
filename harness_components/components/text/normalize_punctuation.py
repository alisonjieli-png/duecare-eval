"""Apply an explicit, auditable punctuation mapping."""
from ._shared import STRING, INTEGER, check, spec
_TRANSLATION = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"', "–": "-", "—": "-", "…": "..."})
SPEC = spec("normalize_punctuation", "Map curly single/double quotes, en/em dashes and ellipsis to explicit ASCII equivalents; a lossy editorial transform.",
    {"text": STRING}, {"text": STRING, "changed_codepoints": INTEGER},
    {"text": "“Hi”—yes…"}, {"text": '"Hi"-yes...', "changed_codepoints": 4})
def run(payload):
    text = check(payload, SPEC)["text"]
    return {"text": text.translate(_TRANSLATION), "changed_codepoints": sum(ord(char) in _TRANSLATION for char in text)}
