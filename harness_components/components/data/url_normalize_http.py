"""Normalize HTTP(S) scheme/host case and default port; preserve path case and query order, refuse userinfo, and perform no host reachability validation."""
from . import _shared as C

SPEC = C.spec("url_normalize_http", "Normalize HTTP(S) scheme/host case and default port; preserve path case and query order, refuse userinfo, and perform no host reachability validation.",
    {'url': C.S}, {'url': C.S},
    {"url": "HTTP://Example.COM:80/Case?b=2&a=1#F"}, {"url": "http://example.com/Case?b=2&a=1#F"}, [C.URL_SOURCE])


def run(payload: dict) -> dict:
    p = C.check(payload, SPEC)
    result = {'url': C.normalize_http(p['url'])}
    return C.finish(result, SPEC)
