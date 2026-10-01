"""Mask supplied spans while preserving code-point count."""
from ._shared import STRING, SPANS, check, valid_spans, merged_spans, spec
SPEC = spec("mask_spans", "Replace each code point inside supplied spans with one mask character; preserves code-point offsets, not byte lengths or display width.",
    {"text": STRING, "spans": SPANS, "mask": STRING}, {"text": STRING, "spans": SPANS},
    {"text": "é🙂abc", "spans": [[0, 2]]}, {"text": "**abc", "spans": [[0, 2]]}, optional=("mask",))
def run(payload):
    p = check(payload, SPEC)
    mask = p.get("mask", "*")
    if len(mask) != 1:
        raise ValueError("mask must contain exactly one code point")
    spans = merged_spans(valid_spans(p["spans"], len(p["text"])))
    chars = list(p["text"])
    for start, end in spans:
        chars[start:end] = [mask] * (end - start)
    return {"text": "".join(chars), "spans": spans}
