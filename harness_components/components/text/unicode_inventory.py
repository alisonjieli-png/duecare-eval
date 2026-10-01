"""Report distinct code points and their first offsets."""
import unicodedata
from collections import Counter
from ._shared import STRING, INTEGER, array, obj, check, spec, UNICODE_SOURCE
SPEC = spec("unicode_inventory", "Report distinct characters in first-seen order with Unicode names, categories, counts and code-point offsets.",
    {"text": STRING}, {"characters": array(obj({"character": STRING, "codepoint": STRING, "name": STRING, "category": STRING, "count": INTEGER, "first_offset": INTEGER}))},
    {"text": "AA"}, {"characters": [{"character": "A", "codepoint": "U+0041", "name": "LATIN CAPITAL LETTER A", "category": "Lu", "count": 2, "first_offset": 0}]},
    sources=(UNICODE_SOURCE,))
SPEC["unicode_database"] = unicodedata.unidata_version
def run(payload):
    text = check(payload, SPEC)["text"]
    counts = Counter(text)
    first = {}
    for index, char in enumerate(text):
        first.setdefault(char, index)
    return {"characters": [{"character": char, "codepoint": f"U+{ord(char):04X}", "name": unicodedata.name(char, ""), "category": unicodedata.category(char), "count": count, "first_offset": first[char]} for char, count in counts.items()]}
