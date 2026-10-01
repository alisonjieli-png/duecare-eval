"""Count Unicode code points, explicitly not grapheme clusters."""
from ._shared import STRING, INTEGER, check, spec
SPEC = spec("codepoint_length", "Count Python Unicode code points; combining sequences and emoji may occupy multiple code points.",
    {"text": STRING}, {"length": INTEGER}, {"text": "e\u0301"}, {"length": 2})
def run(payload):
    return {"length": len(check(payload, SPEC)["text"])}
