"""Remove a URL fragment while preserving the exact preceding URL text, including empty query markers."""
from . import _shared as C

SPEC = C.spec("url_remove_fragment", "Remove a URL fragment while preserving the exact preceding URL text, including empty query markers.",
    {'url': C.S}, {'url': C.S},
    {"url": "https://example.org/A?#here"}, {"url": "https://example.org/A?"}, [C.URL_SOURCE])


def run(payload: dict) -> dict:
    p = C.check(payload, SPEC)
    C.split_url(p['url'])
    result = {'url': p['url'].partition('#')[0]}
    return C.finish(result, SPEC)
