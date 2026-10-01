"""Private validation and metadata helpers; not catalogued operations.

Offsets throughout this family are Python Unicode code-point offsets, not
UTF-8 byte offsets, UTF-16 offsets, grapheme clusters or display columns.
"""

import re

STRING = {"type": "string"}
INTEGER = {"type": "integer"}
BOOLEAN = {"type": "boolean"}
STRINGS = {"type": "array", "items": STRING}
SPAN = {"type": "array", "items": INTEGER, "minItems": 2, "maxItems": 2}
SPANS = {"type": "array", "items": SPAN}
UNICODE_SOURCE = "https://docs.python.org/3/library/unicodedata.html"
REGEX_SOURCE = "https://docs.python.org/3/library/re.html"
EMAIL_SOURCE = "https://www.rfc-editor.org/rfc/rfc5321#section-2.4"


def obj(properties, required=None):
    return {"type": "object", "properties": properties,
            "required": list(properties) if required is None else required,
            "additionalProperties": False}


def array(items):
    return {"type": "array", "items": items}


def integer(minimum=0):
    return {"type": "integer", "minimum": minimum}


def choice(*values):
    return {"type": "string", "enum": list(values)}


def spec(name, description, inputs, outputs, example_input, example_output,
         *, optional=(), sources=()):
    return {"id": "text." + name, "version": "1.0.0",
            "description": description,
            "input_schema": obj(inputs, [k for k in inputs if k not in optional]),
            "output_schema": obj(outputs), "effects": ["pure"],
            "examples": [{"input": example_input, "output": example_output}],
            "sources": list(sources)}


def _validate(value, schema, path):
    expected = schema["type"]
    types = {"string": str, "integer": int, "boolean": bool,
             "array": list, "object": dict}
    if type(value) is not types[expected]:
        raise TypeError(f"{path} must be {expected}")
    if "enum" in schema and value not in schema["enum"]:
        raise ValueError(f"{path} must be one of {schema['enum']}")
    if expected == "integer" and value < schema.get("minimum", value):
        raise ValueError(f"{path} is below its minimum")
    if expected == "array":
        if len(value) < schema.get("minItems", 0) or len(value) > schema.get("maxItems", len(value)):
            raise ValueError(f"{path} has an invalid item count")
        for index, item in enumerate(value):
            _validate(item, schema["items"], f"{path}[{index}]")
    if expected == "object":
        properties = schema["properties"]
        missing = set(schema["required"]) - value.keys()
        unknown = value.keys() - properties.keys()
        if missing or unknown:
            raise ValueError(f"{path} has missing or unknown fields")
        for key, item in value.items():
            _validate(item, properties[key], f"{path}.{key}")


def check(payload, definition):
    _validate(payload, definition["input_schema"], "payload")
    return payload


def nonempty(value, name):
    if not value:
        raise ValueError(f"{name} must not be empty")
    return value


def valid_spans(spans, length):
    for start, end in spans:
        if not 0 <= start <= end <= length:
            raise ValueError("span must satisfy 0 <= start <= end <= text length")
    return spans


def merged_spans(spans, *, touching=True):
    result = []
    for start, end in sorted(spans):
        if start == end:
            continue
        if result and (start <= result[-1][1] if touching else start < result[-1][1]):
            result[-1][1] = max(result[-1][1], end)
        else:
            result.append([start, end])
    return result


def literal_spans(text, needle, overlap=False):
    nonempty(needle, "needle")
    result = []
    position = 0
    while True:
        start = text.find(needle, position)
        if start < 0:
            return result
        result.append([start, start + len(needle)])
        position = start + (1 if overlap else len(needle))


# The supported mailbox profile uses ASCII dot-atoms and DNS-style domains.
_ATEXT = frozenset("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!#$%&'*+-/=?^_`{|}~")
_LABEL = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\Z")


def email_parts(value):
    """Return status, reason, local and domain without inferring delivery."""
    if any(ord(char) < 32 or ord(char) == 127 for char in value):
        return "invalid", "control_character", "", ""
    if any(char in value for char in '\"<>(),;\\'):
        return "unsupported", "quoted_or_header_syntax", "", ""
    if value.count("@") != 1:
        return "invalid", "expected_one_at_sign", "", ""
    local, domain = value.split("@")
    if domain.startswith("[") or domain.endswith("]"):
        return "unsupported", "domain_literal", "", ""
    if not value.isascii():
        return "unsupported", "internationalized_address", "", ""
    if not local or any(not atom or any(c not in _ATEXT for c in atom) for atom in local.split(".")):
        return "invalid", "local_dot_atom", "", ""
    if not domain or any(_LABEL.fullmatch(label) is None for label in domain.split(".")):
        return "invalid", "domain_labels", "", ""
    if len(local) > 64 or len(domain) > 253 or len(value) > 254:
        return "invalid", "length_limit", "", ""
    return "supported", "", local, domain.lower()


EMAIL_OUTPUT = {"status": choice("supported", "invalid", "unsupported"),
                "reason": STRING, "local": STRING, "domain": STRING,
                "normalized": STRING}


def email_record(value):
    status, reason, local, domain = email_parts(value)
    return {"status": status, "reason": reason, "local": local,
            "domain": domain,
            "normalized": local + "@" + domain if status == "supported" else ""}
