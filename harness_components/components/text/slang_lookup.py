"""Lookup caller-supplied meanings without context inference."""
from ._shared import STRING, STRINGS, BOOLEAN, check, spec
from ._lexicon import LEXICON, index_lexicon
SPEC = spec("slang_lookup", "Look up one term in a caller-supplied slang/acronym lexicon; reported meanings are candidates, not inferred contextual or demographic facts.",
    {"term": STRING, "lexicon": LEXICON, "casefold": BOOLEAN},
    {"found": BOOLEAN, "meanings": STRINGS, "ambiguous": BOOLEAN},
    {"term": "OP", "lexicon": [{"term": "op", "meanings": ["original poster", "overpowered"]}]},
    {"found": True, "meanings": ["original poster", "overpowered"], "ambiguous": True}, optional=("casefold",))
def run(payload):
    p = check(payload, SPEC)
    folded = p.get("casefold", True)
    index = index_lexicon(p["lexicon"], folded)
    entry = index.get(p["term"].casefold() if folded else p["term"])
    meanings = list(entry["meanings"]) if entry else []
    return {"found": entry is not None, "meanings": meanings, "ambiguous": len(meanings) > 1}
