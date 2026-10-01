"""Return the exact common code-point suffix."""
from ._shared import STRING, STRINGS, check, spec
SPEC = spec("common_suffix", "Return the exact longest shared code-point suffix of supplied strings; an empty list yields an empty string.",
    {"texts": STRINGS}, {"suffix": STRING}, {"texts": ["walking", "talking"]}, {"suffix": "alking"})
def run(payload):
    texts = check(payload, SPEC)["texts"]
    if not texts:
        return {"suffix": ""}
    shortest = min(texts, key=len)
    index = 0
    while index < len(shortest) and all(text[-index - 1] == shortest[-index - 1] for text in texts):
        index += 1
    return {"suffix": shortest[len(shortest) - index:] if index else ""}
