"""Evaluate required and excluded phrases; optional OR clauses constrain matching only when no required clause exists; an empty query accepts the record."""
from . import _common as C

SPEC = C.spec("evaluate_simple_query", "Evaluate required and excluded phrases; optional OR clauses constrain matching only when no required clause exists; an empty query accepts the record.",
    {'text': C.S, 'query': C.S}, {'accepted': C.B, 'matched_required': C.STRINGS, 'matched_optional': C.STRINGS, 'matched_excluded': C.STRINGS},
    {"text": "red blue sky", "query": "+red \"blue sky\" -green"}, {"accepted": True, "matched_required": ["red"], "matched_optional": ["blue sky"], "matched_excluded": []}, sources=["index", "shlex"])


def run(payload: dict):
    p = C.check(payload, SPEC)
    parts = C.query_parts(p['query'])
    matched = {key: [clause for clause in values if C.phrase_spans(p['text'], clause)] for key, values in parts.items()}
    accepted = len(matched['required']) == len(parts['required']) and (bool(parts['required']) or not parts['optional'] or bool(matched['optional'])) and not matched['excluded']
    result = {'accepted': bool(accepted), 'matched_required': matched['required'], 'matched_optional': matched['optional'], 'matched_excluded': matched['excluded']}
    return C.finish(result, SPEC)
