"""Report whether an authority contains username/password syntax without returning the supplied credentials."""
from . import _shared as C

SPEC = C.spec("url_userinfo", "Report whether an authority contains username/password syntax without returning the supplied credentials.",
    {'url': C.S}, {'has_userinfo': C.B, 'has_password_separator': C.B},
    {"url": "https://u:p@example.org"}, {"has_userinfo": True, "has_password_separator": True}, [C.URL_SOURCE])


def run(payload: dict) -> dict:
    p = C.check(payload, SPEC)
    parts = C.split_url(p['url'])
    result = {'has_userinfo': parts.username is not None or parts.password is not None, 'has_password_separator': parts.password is not None}
    return C.finish(result, SPEC)
