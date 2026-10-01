"""Apply all-required-token and no-excluded-token predicates while returning each missing or forbidden token."""
from . import _common as C

SPEC = C.spec("match_exclusions", "Apply all-required-token and no-excluded-token predicates while returning each missing or forbidden token.",
    {'text': C.S, 'include': C.STRINGS, 'exclude': C.STRINGS}, {'accepted': C.B, 'missing': C.STRINGS, 'excluded_found': C.STRINGS},
    {"text": "red blue", "include": ["red"], "exclude": ["blue"]}, {"accepted": False, "missing": [], "excluded_found": ["blue"]}, sources=["index"])


def run(payload: dict):
    p = C.check(payload, SPEC)
    available = set(C.terms(p['text']))
    required = {word for term in p['include'] for word in C.terms(term)}
    excluded = {word for term in p['exclude'] for word in C.terms(term)}
    missing, found = sorted(required - available), sorted(excluded & available)
    result = {'accepted': not missing and not found, 'missing': missing, 'excluded_found': found}
    return C.finish(result, SPEC)
