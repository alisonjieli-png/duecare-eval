"""Split on whitespace-only lines, preserving intra-paragraph lines."""
from ._shared import STRING, STRINGS, check, spec
SPEC = spec("split_paragraphs", "Group consecutive nonblank Unicode-split lines into paragraphs joined by LF.",
    {"text": STRING}, {"paragraphs": STRINGS},
    {"text": "\na\nb\n \nc\n"}, {"paragraphs": ["a\nb", "c"]})
def run(payload):
    paragraphs, current = [], []
    for line in check(payload, SPEC)["text"].splitlines():
        if line.strip():
            current.append(line)
        elif current:
            paragraphs.append("\n".join(current))
            current = []
    if current:
        paragraphs.append("\n".join(current))
    return {"paragraphs": paragraphs}
