"""Remove selected Unicode control categories with an audit trail."""
import unicodedata
from ._shared import STRING, BOOLEAN, INTEGER, array, obj, check, spec, UNICODE_SOURCE
SPEC = spec("remove_controls", "Remove Cc controls except allowlisted characters; optionally remove Cf format characters, which may change meaning.",
    {"text": STRING, "allow": STRING, "include_format": BOOLEAN},
    {"text": STRING, "removed": array(obj({"offset": INTEGER, "codepoint": STRING}))},
    {"text": "a\x00\tb"}, {"text": "a\tb", "removed": [{"offset": 1, "codepoint": "U+0000"}]},
    optional=("allow", "include_format"), sources=(UNICODE_SOURCE,))
SPEC["unicode_database"] = unicodedata.unidata_version
def run(payload):
    p = check(payload, SPEC)
    categories = {"Cc", "Cf"} if p.get("include_format", False) else {"Cc"}
    allow = set(p.get("allow", "\t\n\r"))
    kept, removed = [], []
    for index, char in enumerate(p["text"]):
        if char not in allow and unicodedata.category(char) in categories:
            removed.append({"offset": index, "codepoint": f"U+{ord(char):04X}"})
        else:
            kept.append(char)
    return {"text": "".join(kept), "removed": removed}
