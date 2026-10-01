"""Return the exact common code-point prefix."""
from ._shared import STRING, STRINGS, check, spec
SPEC = spec("common_prefix", "Return the exact longest shared code-point prefix of supplied strings; an empty list yields an empty string.",
    {"texts": STRINGS}, {"prefix": STRING}, {"texts": ["careful", "caring"]}, {"prefix": "car"})
def run(payload):
    texts = check(payload, SPEC)["texts"]
    if not texts:
        return {"prefix": ""}
    first, last = min(texts), max(texts)
    index = 0
    while index < min(len(first), len(last)) and first[index] == last[index]:
        index += 1
    return {"prefix": first[:index]}
