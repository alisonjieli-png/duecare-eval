"""Parse shell-style quoted search clauses with +required and -excluded prefixes; bare clauses are optional OR terms, not executable shell commands."""
from . import _common as C

SPEC = C.spec("parse_simple_query", "Parse shell-style quoted search clauses with +required and -excluded prefixes; bare clauses are optional OR terms, not executable shell commands.",
    {'query': C.S}, {'required': C.STRINGS, 'optional': C.STRINGS, 'excluded': C.STRINGS},
    {"query": "+red \"blue sky\" -green"}, {"required": ["red"], "optional": ["blue sky"], "excluded": ["green"]}, sources=["shlex"])


def run(payload: dict):
    p = C.check(payload, SPEC)
    result = C.query_parts(p['query'])
    return C.finish(result, SPEC)
