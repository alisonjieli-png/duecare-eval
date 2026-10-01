"""Append encoded string pairs without changing existing raw query pairs or the fragment."""
from . import _shared as C
from urllib.parse import urlencode

SPEC = C.spec("url_query_append", "Append encoded string pairs without changing existing raw query pairs or the fragment.",
    {'url': C.S, 'pairs': C.PAIRS}, {'url': C.S},
    {"url": "https://example.org/A?a=1#f", "pairs": [["a", "2"], ["q", "x y"]]}, {"url": "https://example.org/A?a=1&a=2&q=x+y#f"}, [C.URL_SOURCE])


def run(payload: dict) -> dict:
    p = C.check(payload, SPEC)
    parts = C.split_url(p['url'])
    C.query_pairs(parts.query)
    new = urlencode(C.string_pairs(p['pairs']), encoding='utf-8', errors='strict')
    query = parts.query + ('&' if parts.query and new else '') + new
    result = {'url': C.with_query(p['url'], query) if new else p['url']}
    return C.finish(result, SPEC)
