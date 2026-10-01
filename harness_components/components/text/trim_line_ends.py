"""Remove only ASCII spaces and tabs before line terminators."""
from ._shared import STRING, check, spec
SPEC = spec("trim_line_ends", "Remove trailing ASCII spaces and tabs per line while preserving original line endings.",
    {"text": STRING}, {"text": STRING},
    {"text": "a \r\nb\t\n"}, {"text": "a\r\nb\n"})
def run(payload):
    text = check(payload, SPEC)["text"]
    result = []
    for line in text.splitlines(keepends=True):
        body = line.rstrip("\r\n\v\f\x1c\x1d\x1e\x85\u2028\u2029")
        result.append(body.rstrip(" \t") + line[len(body):])
    return {"text": "".join(result)}
