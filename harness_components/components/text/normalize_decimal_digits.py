"""Map Unicode decimal digits to corresponding ASCII digits."""
import unicodedata
from ._shared import STRING, INTEGER, check, spec, UNICODE_SOURCE
SPEC = spec("normalize_decimal_digits", "Convert Unicode decimal digits (Nd) to ASCII; leave other numeric characters unchanged.",
    {"text": STRING}, {"text": STRING, "changed": INTEGER},
    {"text": "١２²"}, {"text": "12²", "changed": 2}, sources=(UNICODE_SOURCE,))
SPEC["unicode_database"] = unicodedata.unidata_version
def run(payload):
    text = check(payload, SPEC)["text"]
    converted = "".join(str(unicodedata.decimal(char)) if unicodedata.category(char) == "Nd" else char for char in text)
    return {"text": converted, "changed": sum(a != b for a, b in zip(text, converted))}
