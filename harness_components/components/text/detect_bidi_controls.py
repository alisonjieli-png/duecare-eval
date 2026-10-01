"""Locate Unicode Bidi_Control characters without editing text."""
import unicodedata
from ._shared import STRING, INTEGER, array, obj, check, spec
_CONTROLS = frozenset("\u061c\u200e\u200f\u202a\u202b\u202c\u202d\u202e\u2066\u2067\u2068\u2069")
SPEC = spec("detect_bidi_controls", "Locate explicit Unicode Bidi_Control code points; their presence alone does not imply malicious text.",
    {"text": STRING}, {"controls": array(obj({"offset": INTEGER, "codepoint": STRING, "name": STRING}))},
    {"text": "a\u202eb"}, {"controls": [{"offset": 1, "codepoint": "U+202E", "name": "RIGHT-TO-LEFT OVERRIDE"}]},
    sources=("https://www.unicode.org/reports/tr9/",))
def run(payload):
    return {"controls": [{"offset": i, "codepoint": f"U+{ord(char):04X}", "name": unicodedata.name(char, "")} for i, char in enumerate(check(payload, SPEC)["text"]) if char in _CONTROLS]}
