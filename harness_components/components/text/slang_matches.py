"""Match lexicon word tokens while preserving original offsets."""
from ._shared import STRING, STRINGS, INTEGER, BOOLEAN, array, obj, check, spec
from ._lexicon import LEXICON, index_lexicon, matches
MATCH = obj({"text": STRING, "term": STRING, "start": INTEGER, "end": INTEGER, "meanings": STRINGS, "ambiguous": BOOLEAN})
SPEC = spec("slang_matches", "Match whole Python-regex word tokens against a caller-supplied lexicon; candidate meanings do not establish contextual meaning or speaker attributes.",
    {"text": STRING, "lexicon": LEXICON, "casefold": BOOLEAN}, {"matches": array(MATCH)},
    {"text": "IDK.", "lexicon": [{"term": "idk", "meanings": ["I do not know"]}]},
    {"matches": [{"text": "IDK", "term": "idk", "start": 0, "end": 3, "meanings": ["I do not know"], "ambiguous": False}]}, optional=("casefold",))
def run(payload):
    p = check(payload, SPEC)
    folded = p.get("casefold", True)
    return {"matches": matches(p["text"], index_lexicon(p["lexicon"], folded), folded)}
