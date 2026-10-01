"""Find uppercase ASCII runs; do not infer their expansion."""
import re
from ._shared import STRING, INTEGER, array, obj, check, spec
SPEC = spec("acronym_candidates", "Find whole ASCII uppercase tokens of two or more letters; these are candidates, not verified acronyms.",
    {"text": STRING}, {"candidates": array(obj({"text": STRING, "start": INTEGER, "end": INTEGER}))},
    {"text": "API and X HTTP2"}, {"candidates": [{"text": "API", "start": 0, "end": 3}]})
def run(payload):
    return {"candidates": [{"text": m.group(), "start": m.start(), "end": m.end()} for m in re.finditer(r"(?<!\w)[A-Z]{2,}(?!\w)", check(payload, SPEC)["text"])]}
