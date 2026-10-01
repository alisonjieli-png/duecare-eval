"""Return the normalized scheme/authority origin of an absolute HTTP(S) URL; refuse userinfo."""
from . import _shared as C

SPEC = C.spec("url_origin", "Return the normalized scheme/authority origin of an absolute HTTP(S) URL; refuse userinfo.",
    {'url': C.S}, {'origin': C.S},
    {"url": "https://EXAMPLE.org:443/A?q=1"}, {"origin": "https://example.org"}, [C.URL_SOURCE])


def run(payload: dict) -> dict:
    p = C.check(payload, SPEC)
    parts = C.split_url(C.normalize_http(p['url']))
    result = {'origin': parts.scheme + '://' + parts.netloc}
    return C.finish(result, SPEC)
