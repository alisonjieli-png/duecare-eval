"""Count Unicode general categories in sorted category order."""
import unicodedata
from collections import Counter
from ._shared import STRING, INTEGER, array, obj, check, spec, UNICODE_SOURCE
SPEC = spec("unicode_category_counts", "Count Unicode general-category labels without inferring language or writing system.",
    {"text": STRING}, {"categories": array(obj({"category": STRING, "count": INTEGER}))},
    {"text": "A1 "}, {"categories": [{"category": "Lu", "count": 1}, {"category": "Nd", "count": 1}, {"category": "Zs", "count": 1}]}, sources=(UNICODE_SOURCE,))
SPEC["unicode_database"] = unicodedata.unidata_version
def run(payload):
    counts = Counter(unicodedata.category(char) for char in check(payload, SPEC)["text"])
    return {"categories": [{"category": category, "count": counts[category]} for category in sorted(counts)]}
