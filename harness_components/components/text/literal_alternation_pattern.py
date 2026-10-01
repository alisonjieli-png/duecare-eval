"""Build a regex from escaped literals only."""
import re
from ._shared import STRING, STRINGS, check, nonempty, spec, REGEX_SOURCE
SPEC = spec("literal_alternation_pattern", "Build a noncapturing Python regex alternation from unique escaped nonempty literals, longest first; empty input matches nothing.",
    {"literals": STRINGS}, {"pattern": STRING},
    {"literals": ["+", "++", "+"]}, {"pattern": "(?:\\+\\+|\\+)"}, sources=(REGEX_SOURCE,))
def run(payload):
    literals = check(payload, SPEC)["literals"]
    for value in literals:
        nonempty(value, "literal")
    ordered = sorted(dict.fromkeys(literals), key=lambda value: -len(value))
    return {"pattern": "(?:" + "|".join(re.escape(value) for value in ordered) + ")" if ordered else "(?!)"}
