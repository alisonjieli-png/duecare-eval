"""Produce Python's Unicode caseless comparison form."""
from ._shared import STRING, BOOLEAN, check, spec
SPEC = spec("casefold_text", "Apply Unicode casefold for caseless comparison; this can expand characters and is not identity normalization.",
    {"text": STRING}, {"text": STRING, "changed": BOOLEAN},
    {"text": "Straße"}, {"text": "strasse", "changed": True},
    sources=("https://docs.python.org/3/library/stdtypes.html#str.casefold",))
def run(payload):
    text = check(payload, SPEC)["text"]
    folded = text.casefold()
    return {"text": folded, "changed": folded != text}
