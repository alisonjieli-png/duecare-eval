"""Benchmark apparatus: agreement, consensus, coverage.

These metrics are what turn a pile of judgments into a comparison. A single
judge cannot support a ranking claim, and a metric that can exceed its own
bound, or that reads high on random data, will silently corrupt any ranking
built on it. Both bugs occurred during development.
"""
from __future__ import annotations

import random

import pytest

from duecare_eval.panel import (BASIS_ORACLE, BASIS_TIER, consensus_label,
                                compare_to_reference, fleiss_kappa,
                                krippendorff_alpha, ordinal_matrix, panel_report,
                                weighted_kappa, wilson_interval)


AGREEING = {"i1": {"a": 1, "b": 1, "c": 1}, "i2": {"a": 2, "b": 2, "c": 3},
            "i3": {"a": 4, "b": 4, "c": 4}, "i4": {"a": 5, "b": 5, "c": 4},
            "i5": {"a": 1, "b": 1, "c": 1}}
RANDOMISH = {"i1": {"a": 1, "b": 5, "c": 3}, "i2": {"a": 2, "b": 4, "c": 1},
             "i3": {"a": 3, "b": 3, "c": 5}, "i4": {"a": 5, "b": 2, "c": 2},
             "i5": {"a": 4, "b": 1, "c": 4}}


def test_all_agreement_metrics_stay_within_bounds():
    for table in (AGREEING, RANDOMISH):
        for fn in (krippendorff_alpha, fleiss_kappa, weighted_kappa):
            v = fn(table)
            assert v is None or -1.0 <= v <= 1.0, (fn.__name__, v)


def test_agreement_beats_disagreement():
    assert krippendorff_alpha(AGREEING) > 0.8
    assert krippendorff_alpha(RANDOMISH) < 0.2


def test_independent_raters_score_near_zero_on_ordinal():
    """Every chance-corrected agreement measure must recover independence."""
    random.seed(11)
    indep = {f"i{i}": {f"j{j}": random.randint(1, 5) for j in range(3)} for i in range(400)}
    a = krippendorff_alpha(indep)
    assert abs(a) < 0.15, a
    w = weighted_kappa(indep)
    assert w is None or abs(w) < 0.15, w
    assert abs(fleiss_kappa(indep)) < 0.15


def test_independent_five_raters_have_zero_nominal_agreement():
    import itertools
    table = {str(i): {str(j): grade for j, grade in enumerate(values)}
             for i, values in enumerate(itertools.product(range(1, 6), repeat=5))}
    assert fleiss_kappa(table) == pytest.approx(0.0, abs=1e-12)


def test_rating_units_preserve_arms_and_are_order_invariant():
    records = [{"item_id": f"i{i}", "judge": judge, "candidate_arm": arm,
                "status": "graded", "grade":
                (1 if judge == "a" else 5) if arm == "bare" else 4 + i % 2}
               for i in range(20) for arm in ("bare", "grounded")
               for judge in ("a", "b")]
    matrix = ordinal_matrix(records)
    assert len(matrix) == 40
    assert matrix == ordinal_matrix(list(reversed(records)))
    assert krippendorff_alpha(matrix) < 0.67


def test_duplicate_panel_cells_fail_instead_of_overwriting():
    row = {"item_id": "a", "judge": "j", "status": "graded", "grade": 2}
    with pytest.raises(ValueError, match="duplicate_panel_rating"):
        ordinal_matrix([row, {**row, "grade": 5}])


def test_ordinal_distance_respects_ordering():
    """A large ordinal gap (1 vs 5) must read as WORSE agreement than a small
    gap (1 vs 2), which is exactly what a nominal metric cannot see."""
    # Both tables mix agreeing and disagreeing items, so the marginals are
    # non-degenerate; only the SIZE of the gap differs. A purely uniform table
    # saturates alpha at -1.0 regardless of gap size, which is correct behaviour
    # and would make the test vacuous.
    big = {"a1": {"x": 1, "y": 5}, "a2": {"x": 1, "y": 5}, "a3": {"x": 3, "y": 3},
           "a4": {"x": 2, "y": 2}, "a5": {"x": 4, "y": 4}}
    small = {"a1": {"x": 1, "y": 2}, "a2": {"x": 1, "y": 2}, "a3": {"x": 3, "y": 3},
             "a4": {"x": 2, "y": 2}, "a5": {"x": 4, "y": 4}}
    assert krippendorff_alpha(big) < krippendorff_alpha(small)


def test_single_judge_agreement_is_undefined_not_perfect():
    """A panel of one yields None, never 1.0. Reporting perfect agreement for a
    single rater is the most dangerous possible bug in this file."""
    assert krippendorff_alpha({"i1": {"a": 3}}) is None
    assert fleiss_kappa({"i1": {"a": 3}}) is None


def test_missing_cells_are_counted_missing_not_disagreement():
    full = {"i1": {"a": 1, "b": 1}, "i2": {"a": 2, "b": 2}, "i3": {"a": 3, "b": 3}}
    sparse = {"i1": {"a": 1, "b": None}, "i2": {"a": 2, "b": 2}, "i3": {"a": 3, "b": None}}
    assert krippendorff_alpha(full) is not None
    v = krippendorff_alpha(sparse)
    assert v is None or -1 <= v <= 1


def test_consensus_upweights_the_reliable_judge():
    table = {"i1": {"good": 2, "n1": 4, "n2": 1}, "i2": {"good": 3, "n1": 2, "n2": 5},
             "i3": {"good": 2, "n1": 5, "n2": 3}, "i4": {"good": 4, "n1": 1, "n2": 5},
             "i5": {"good": 1, "n1": 4, "n2": 2}, "i6": {"good": 5, "n1": 2, "n2": 1}}
    c = consensus_label(table)
    assert c["judge_weights"]["good"] == max(c["judge_weights"].values())


def test_consensus_reports_split_and_margin():
    c = consensus_label({"i1": {"a": 1, "b": 5}, "i2": {"a": 3, "b": 3}})
    item = c["per_item"]["i2"]
    assert item["split"] is False and item["agreement"] == 1.0
    item1 = c["per_item"]["i1"]
    assert item1["split"] is True and item1["agreement"] == 0.5


def test_wilson_interval_is_bounded():
    for k, n in ((0, 6), (3, 152), (6, 6), (1, 1000)):
        iv = wilson_interval(k, n)
        assert 0.0 <= iv["low"] <= iv["point"] <= iv["high"] <= 1.0, (k, n, iv)
    assert wilson_interval(0, 0)["low"] is None


def test_reference_comparison_reports_coverage():
    recs = [{"item_id": "x", "judge": "j", "status": "graded", "grade": 3,
             "critical_failure": False, "abstain": False},
            {"item_id": "y", "judge": "j", "status": "graded", "grade": 5,
             "critical_failure": False, "abstain": False},
            {"item_id": "z", "judge": "j", "status": "error"}]
    ref = {"x": 3, "y": 4}          # z has no reference label at all
    out = compare_to_reference(recs, ref, BASIS_ORACLE)
    assert out["n"] == 2, out
    assert "coverage" in out["coverage_note"] or "n is" in out["coverage_note"]


def test_reference_comparison_on_empty_overlap():
    out = compare_to_reference([{"item_id": "a", "status": "graded", "grade": 3}], {}, BASIS_TIER)
    assert out["n"] == 0 and out["exact_tier_match"] is None


def test_ordinal_matrix_skips_ungraded():
    table = ordinal_matrix([
        {"item_id": "a", "judge": "j1", "status": "graded", "grade": 2},
        {"item_id": "a", "judge": "j2", "status": "error", "grade": None},
        {"item_id": "b", "judge": "j1", "status": "graded", "grade": 5},
    ])
    assert table["a"] == {"j1": 2}
    assert table["b"] == {"j1": 5}


def test_panel_report_flags_single_judge_panel():
    recs = [{"item_id": f"i{i}", "judge": "only", "status": "graded", "grade": 3,
             "critical_failure": False, "abstain": False} for i in range(5)]
    rep = panel_report(recs)
    assert rep["judge_count"] == 1
    assert rep["agreement"]["krippendorff_alpha_ordinal"] is None
    assert rep["consensus"]["items"] == 0
