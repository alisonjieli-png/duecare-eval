"""Convert CRLF and CR into LF, optionally then CRLF."""
from ._shared import STRING, choice, check, spec
SPEC = spec("normalize_newlines", "Normalize CRLF and CR line endings; preserve other Unicode separators.",
    {"text": STRING, "newline": choice("lf", "crlf")}, {"text": STRING},
    {"text": "a\r\nb\rc"}, {"text": "a\nb\nc"}, optional=("newline",))
def run(payload):
    p = check(payload, SPEC)
    text = p["text"].replace("\r\n", "\n").replace("\r", "\n")
    return {"text": text.replace("\n", "\r\n") if p.get("newline", "lf") == "crlf" else text}
