"""Return the SHA-256 digest of exact UTF-8 string bytes; no normalization or authenticity claim."""
from . import _shared as C
from hashlib import sha256

SPEC = C.spec("sha256_utf8", "Return the SHA-256 digest of exact UTF-8 string bytes; no normalization or authenticity claim.",
    {'text': C.S}, {'sha256': C.S},
    {"text": "abc"}, {"sha256": "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"}, ['https://docs.python.org/3/library/hashlib.html'])


def run(payload: dict) -> dict:
    p = C.check(payload, SPEC)
    result = {'sha256': sha256(p['text'].encode('utf-8')).hexdigest()}
    return C.finish(result, SPEC)
