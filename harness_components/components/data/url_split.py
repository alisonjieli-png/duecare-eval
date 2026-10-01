"""Split a provided URL without network access; reject malformed percent escapes, controls and invalid ports, and report userinfo presence."""
from . import _shared as C

SPEC = C.spec("url_split", "Split a provided URL without network access; reject malformed percent escapes, controls and invalid ports, and report userinfo presence.",
    {'url': C.S}, {'scheme': C.S, 'authority': C.S, 'path': C.S, 'query': C.S, 'fragment': C.S, 'hostname': C.ANY, 'port': C.ANY, 'has_userinfo': C.B},
    {"url": "https://Example.org:8443/A?x=1#b"}, {"scheme": "https", "authority": "Example.org:8443", "path": "/A", "query": "x=1", "fragment": "b", "hostname": "example.org", "port": 8443, "has_userinfo": False}, [C.URL_SOURCE])


def run(payload: dict) -> dict:
    p = C.check(payload, SPEC)
    parts = C.split_url(p['url'])
    result = {'scheme': parts.scheme, 'authority': parts.netloc, 'path': parts.path, 'query': parts.query, 'fragment': parts.fragment, 'hostname': parts.hostname, 'port': parts.port, 'has_userinfo': parts.username is not None or parts.password is not None}
    return C.finish(result, SPEC)
