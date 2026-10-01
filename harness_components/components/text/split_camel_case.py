"""Split ASCII camel-case transitions and separators."""
import re
from ._shared import STRING, STRINGS, check, spec
SPEC = spec("split_camel_case", "Split ASCII lower/digit-to-upper and acronym-to-title transitions, then underscores, hyphens and whitespace; preserve other characters.",
    {"text": STRING}, {"parts": STRINGS},
    {"text": "HTTPServer_v2Client"}, {"parts": ["HTTP", "Server", "v2", "Client"]})
def run(payload):
    text = check(payload, SPEC)["text"]
    text = re.sub(r"([A-Z])([A-Z][a-z])", r"\1 \2", text)
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    return {"parts": [part for part in re.split(r"[_\s-]+", text) if part]}
