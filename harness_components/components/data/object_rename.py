"""Rename existing object keys simultaneously; reject destination collisions and nonstring names."""
from . import _shared as C

SPEC = C.spec("object_rename", "Rename existing object keys simultaneously; reject destination collisions and nonstring names.",
    {'object': C.O, 'mapping': C.O}, {'object': C.O},
    {"object": {"a": 1, "b": 2}, "mapping": {"a": "c"}}, {"object": {"c": 1, "b": 2}}, [C.JSON_SOURCE])


def run(payload: dict) -> dict:
    p = C.check(payload, SPEC)
    C.keys_present(p['object'], list(p['mapping']))
    C.require(all(type(value) is str for value in p['mapping'].values()), 'string_rename_target_required')
    names = [p['mapping'].get(key, key) for key in p['object']]
    C.require(len(names) == len(set(names)), 'rename_collision')
    result = {'object': {p['mapping'].get(key, key): value for key, value in p['object'].items()}}
    return C.finish(result, SPEC)
