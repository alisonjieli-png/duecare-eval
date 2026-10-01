"""Compute linear-gain discounted cumulative gain sum(gain/log2(one_based_rank+1)); supplied gains are already utilities, with no implicit exponential transform."""
from . import _common as C

SPEC = C.spec("dcg_at_k", "Compute linear-gain discounted cumulative gain sum(gain/log2(one_based_rank+1)); supplied gains are already utilities, with no implicit exponential transform.",
    {'gains': C.arr(C.number(0)), 'k': C.I}, {'dcg': C.N, 'evaluated_ranks': C.I},
    {"gains": [3, 0, 1], "k": 3}, {"dcg": 3.5, "evaluated_ranks": 3}, sources=["metrics"])


def run(payload: dict):
    p = C.check(payload, SPEC)
    result = {'dcg': C.dcg(p['gains'], p['k']), 'evaluated_ranks': min(p['k'], len(p['gains']))}
    return C.finish(result, SPEC)
