"""Compare two supplied byte arrays using the standard comparison primitive; returns equality without authentication claims."""
from . import _shared as C
import hmac

SPEC = C.spec("bytes_equal", "Compare two supplied byte arrays using the standard comparison primitive; returns equality without authentication claims.",
    {'left': C.BYTES, 'right': C.BYTES}, {'equal': C.B},
    {"left": [0, 255], "right": [0, 255]}, {"equal": True}, ['https://docs.python.org/3/library/hmac.html#hmac.compare_digest'])


def run(payload: dict) -> dict:
    p = C.check(payload, SPEC)
    result = {'equal': hmac.compare_digest(bytes(p['left']), bytes(p['right']))}
    return C.finish(result, SPEC)
