"""Apply only unambiguous caller-supplied lexical substitutions."""
from ._shared import STRING, INTEGER, BOOLEAN, SPANS, check, spec
from ._lexicon import LEXICON, index_lexicon, matches
SPEC = spec("expand_lexicon", "Replace matched word tokens only when the supplied lexicon lists exactly one meaning; preserve ambiguous matches and report original spans. This is a literal editorial transform.",
    {"text": STRING, "lexicon": LEXICON, "casefold": BOOLEAN},
    {"text": STRING, "replaced": INTEGER, "ambiguous_spans": SPANS},
    {"text": "idk OP", "lexicon": [{"term": "idk", "meanings": ["I do not know"]}, {"term": "op", "meanings": ["original poster", "overpowered"]}]},
    {"text": "I do not know OP", "replaced": 1, "ambiguous_spans": [[4, 6]]}, optional=("casefold",))
def run(payload):
    p = check(payload, SPEC)
    folded = p.get("casefold", True)
    found = matches(p["text"], index_lexicon(p["lexicon"], folded), folded)
    result, end, replaced, ambiguous = [], 0, 0, []
    for match in found:
        result.append(p["text"][end:match["start"]])
        if match["ambiguous"]:
            result.append(match["text"])
            ambiguous.append([match["start"], match["end"]])
        else:
            result.append(match["meanings"][0])
            replaced += 1
        end = match["end"]
    result.append(p["text"][end:])
    return {"text": "".join(result), "replaced": replaced, "ambiguous_spans": ambiguous}
