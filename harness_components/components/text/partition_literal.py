"""Partition on the first or last literal occurrence."""
from ._shared import STRING, BOOLEAN, check, nonempty, spec
SPEC = spec("partition_literal", "Partition at the first or last exact separator, returning an explicit found flag.",
    {"text": STRING, "separator": STRING, "last": BOOLEAN},
    {"before": STRING, "separator": STRING, "after": STRING, "found": BOOLEAN},
    {"text": "a=b=c", "separator": "=", "last": True}, {"before": "a=b", "separator": "=", "after": "c", "found": True},
    optional=("last",))
def run(payload):
    p = check(payload, SPEC)
    separator = nonempty(p["separator"], "separator")
    before, found, after = p["text"].rpartition(separator) if p.get("last", False) else p["text"].partition(separator)
    return {"before": before, "separator": found, "after": after, "found": bool(found)}
