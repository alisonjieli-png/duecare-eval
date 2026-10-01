"""Remove all query pairs whose decoded names match requested keys; preserve surviving raw pair bytes/order and fragment."""
from . import _shared as C

SPEC = C.spec("url_query_remove", "Remove all query pairs whose decoded names match requested keys; preserve surviving raw pair bytes/order and fragment.",
    {'url': C.S, 'keys': C.STRINGS}, {'url': C.S},
    {"url": "https://example.org/A?a=1&q=a%20b&a=2#f", "keys": ["a"]}, {"url": "https://example.org/A?q=a%20b#f"}, [C.URL_SOURCE])


def run(payload: dict) -> dict:
    p = C.check(payload, SPEC)
    parts = C.split_url(p['url'])
    C.query_pairs(parts.query)
    kept = [pair for pair in parts.query.split('&') if C.percent_decode(pair.partition('=')[0], plus=True) not in p['keys']]
    query = '&'.join(kept)
    result = {'url': p['url'] if query == parts.query else C.with_query(p['url'], query)}
    return C.finish(result, SPEC)
