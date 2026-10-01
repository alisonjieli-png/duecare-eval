"""Hash UTF-8 compact sorted-key Python JSON; this is a documented representation digest, not RFC 8785 canonicalization."""
from . import _shared as C
from hashlib import sha256

SPEC = C.spec("json_digest", "Hash UTF-8 compact sorted-key Python JSON; this is a documented representation digest, not RFC 8785 canonicalization.",
    {'value': C.ANY}, {'sha256': C.S},
    {"value": {}}, {"sha256": "44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a"}, [C.JSON_SOURCE, 'https://docs.python.org/3/library/hashlib.html'])


def run(payload: dict) -> dict:
    p = C.check(payload, SPEC)
    result = {'sha256': sha256(C.compact(p['value'], sort_keys=True).encode('utf-8')).hexdigest()}
    return C.finish(result, SPEC)
