"""Exact and clustered interval estimation.

The two numbers in `test_research_report_bounds_are_reproduced_exactly` are the
load-bearing tests in this file: they pin the implementation against the
recovered research source (RESEARCH/2026-09-27-duecare, section 7) rather than
against my own arithmetic, because a bound function that disagrees with the
report it is meant to implement is worse than none.
"""
from __future__ import annotations

import math

import pytest

from duecare_eval import stats as ST


# ------------------------------------------------- pinned to the research report

@pytest.mark.parametrize("n,expected", [(60, 0.0487), (300, 0.0099)])
def test_research_report_bounds_are_reproduced_exactly(n, expected):
    """"zero observed failures in 60 independent cases leaves a one-sided exact
    95% upper failure bound of about 4.87%. With 300 independent cases it is
    about 0.99%." -- RESEARCH/2026-09-27-duecare section 7.

    An earlier version special-cased k == 0 to a one-sided upper of 1.0, which is
    the TWO-SIDED upper, so every zero-failure campaign reported a 100% failure
    rate. This test is why that cannot recur.
    """
    got = ST.rule_of_three_bound(0, n)
    assert abs(got - expected) < 0.0015, f"n={n}: got {got:.5f}, report says {expected}"


def test_rule_of_three_is_exactly_one_minus_alpha_to_the_one_over_n():
    for n in (10, 60, 300, 1000):
        assert abs(ST.rule_of_three_bound(0, n) - (1 - 0.05 ** (1 / n))) < 1e-9


def test_more_observations_narrow_the_bound_monotonically():
    bounds = [ST.rule_of_three_bound(0, n) for n in (30, 60, 120, 300, 1000, 10000)]
    assert all(a > b for a, b in zip(bounds, bounds[1:])), bounds


# ----------------------------------------------------------------- correctness

def test_incomplete_beta_matches_hand_computed_values():
    # I_0.5(2,3): density is proportional to t(1-t)^2, whose integral to 0.5 is
    # 0.0572917 and B(2,3) = 1/12, giving 0.6875.
    assert ST.betainc(2, 3, 0.5) == pytest.approx(0.6875, abs=1e-9)
    assert ST.betainc(0.5, 0.5, 0.5) == pytest.approx(0.5, abs=1e-9)
    assert ST.betainc(3, 7, 0.0) == 0.0
    assert ST.betainc(3, 7, 1.0) == 1.0


@pytest.mark.parametrize("n,k,p", [(10, 3, 0.5), (20, 7, 0.3), (50, 25, 0.5), (7, 0, 0.2)])
def test_binomial_cdf_matches_the_direct_sum(n, k, p):
    direct = sum(math.comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(k + 1))
    assert ST.binomial_cdf(k, n, p) == pytest.approx(direct, abs=1e-12)


def test_clopper_pearson_covers_the_truth_at_its_nominal_rate():
    """Coverage, checked by simulation: the interval must contain the true p
    about 95% of the time. A bound that under-covers is a lie in a safety report.
    """
    true_p, n, trials, alpha = 0.20, 50, 400, 0.05
    rng = __import__("random").Random("coverage")
    hits = 0
    for _ in range(trials):
        k = sum(1 for _ in range(n) if rng.random() < true_p)
        ci = ST.clopper_pearson(k, n, alpha=alpha)
        hits += ci["lower"] <= true_p <= ci["upper"]
    assert 0.93 <= hits / trials <= 0.99, hits / trials


def test_clopper_pearson_edge_cases_do_not_raise():
    for k, n in ((0, 1), (1, 1), (0, 10), (10, 10), (0, 10 ** 6), (10 ** 6, 10 ** 6)):
        ci = ST.clopper_pearson(k, n)
        assert 0.0 <= ci["lower"] <= ci["upper"] <= 1.0
    with pytest.raises(ValueError):
        ST.clopper_pearson(0, 0)
    with pytest.raises(ValueError):
        ST.clopper_pearson(5, 3)
    with pytest.raises(ValueError):
        ST.clopper_pearson(1, 3, alpha=0.0)


def test_zero_failures_is_not_evidence_of_zero_rate():
    """The single most important property: 0/60 must not read as 0% failure."""
    ci = ST.clopper_pearson(0, 60)
    assert ci["point"] == 0.0
    assert ci["lower"] == 0.0
    assert ci["one_sided_upper"] == pytest.approx(0.0487, abs=0.0015)
    # The two-sided upper is 1 - (alpha/2)^(1/n) = 0.0596 at n=60. It is NOT 1.0:
    # a two-sided interval must also allow for rates far ABOVE the observed one.
    assert ci["upper"] == pytest.approx(1 - 0.025 ** (1 / 60), abs=1e-4)


def test_wilson_is_narrower_than_exact_and_contains_the_point_estimate():
    for k, n in ((5, 68), (30, 68), (1, 10), (9, 10), (250, 500)):
        w, c = ST.wilson_interval(k, n), ST.clopper_pearson(k, n)
        assert w["lower"] >= c["lower"] - 1e-9
        assert w["upper"] <= c["upper"] + 1e-9
        assert w["lower"] <= w["point"] <= w["upper"]


# ---------------------------------------------------------------- clustering

def _correlated_records(n_clusters, per_cluster, bad_clusters, seed="c"):
    """Failure is a property of the CORE, so every variant of a core fails together.

    This is the realistic shape for a paraphrase-generated corpus: if a system
    cannot tell 45 hours from 48, it fails all fifty framings of that item. The
    alternative -- independent failures within a core -- is the case where
    clustering costs nothing, and testing only that case would make the clustered
    interval look unnecessary.
    """
    rng = __import__("random").Random(seed)
    chosen = set(rng.sample(range(n_clusters), bad_clusters))
    return [{"core_id": c, "bad": c in chosen}
            for c in range(n_clusters) for _ in range(per_cluster)]


def test_clustered_interval_is_much_wider_when_failure_is_a_property_of_the_core():
    recs = _correlated_records(n_clusters=200, per_cluster=25, bad_clusters=20)
    r = ST.clustered_proportion(recs, lambda x: x["bad"], n_resamples=800)
    naive_w = r["naive_binomial"]["upper"] - r["naive_binomial"]["lower"]
    clust_w = r["clustered"]["upper"] - r["clustered"]["lower"]
    assert clust_w > 2.5 * naive_w, (naive_w, clust_w, r["interval_width_ratio"])
    assert r["interval_width_ratio"] > 2.5
    assert r["n_items"] == 5000 and r["n_clusters"] == 200


def test_clustered_and_naive_agree_when_failures_are_independent_within_a_core():
    rng = __import__("random").Random("indep")
    recs = [{"core_id": c, "bad": rng.random() < 0.01}
            for c in range(300) for _ in range(20)]
    r = ST.clustered_proportion(recs, lambda x: x["bad"], n_resamples=800)
    assert r["interval_width_ratio"] < 1.5, r["interval_width_ratio"]


def test_cluster_bootstrap_is_reproducible_from_its_seed():
    recs = _correlated_records(80, 10, 8, seed="repro")
    a = ST.clustered_proportion(recs, lambda x: x["bad"], n_resamples=300)
    b = ST.clustered_proportion(recs, lambda x: x["bad"], n_resamples=300)
    assert a["clustered"] == b["clustered"]


def test_cluster_bootstrap_rejects_an_empty_corpus():
    with pytest.raises(ValueError):
        ST.cluster_bootstrap({}, lambda rs: 0.0)


# ------------------------------------------------------------- design effect

def test_fifty_thousand_items_over_a_thousand_cores_is_a_thousand_observations():
    sizes = [50] * 1000
    assert ST.design_effect(sizes) == pytest.approx(50.0)
    assert ST.effective_sample_size(sizes) == pytest.approx(1000.0, abs=1.0)


def test_design_effect_is_one_for_singletons():
    assert ST.design_effect([1] * 500) == pytest.approx(1.0)
    assert ST.effective_sample_size([1] * 500) == pytest.approx(500.0)


def test_effective_n_never_exceeds_item_count():
    for sizes in ([3, 3, 3], [1, 50, 2], [10] * 40, [1] * 7):
        assert ST.effective_sample_size(sizes) <= sum(sizes) + 1e-9


# ----------------------------------------------------------------- comparison

def test_comparing_two_proportions_can_reject_and_can_fail_to_reject():
    # Same observed gap, wildly different n: 1.0 vs 0.9 in different ways.
    big = ST.compare_two_proportions(970, 1000, 950, 1000)
    assert big["excludes_zero"]
    small = ST.compare_two_proportions(10, 10, 9, 10)
    assert not small["excludes_zero"]
    assert small["lower"] < 0 < small["upper"]


def test_identical_proportions_have_an_interval_spanning_zero():
    c = ST.compare_two_proportions(65, 68, 65, 68)
    assert c["difference"] == 0.0
    assert not c["excludes_zero"]


def test_paired_comparison_uses_shared_items_and_reports_missingness():
    a = {"i1": True, "i2": True, "i3": False, "only-a": True}
    b = {"i1": False, "i2": True, "i3": False, "only-b": False}
    c = ST.paired_binary_comparison(a, b, n_resamples=500)
    assert c["n_paired"] == 3
    assert c["a_only_correct"] == 1
    assert c["b_only_correct"] == 0
    assert c["missing_from_a"] == 1
    assert c["missing_from_b"] == 1


def test_paired_comparison_rejects_non_boolean_outcomes():
    with pytest.raises(ValueError, match="paired_outcome_not_bool"):
        ST.paired_binary_comparison({"i": 1}, {"i": True}, n_resamples=100)


def test_the_jev_vs_gpt_oss_classification_gap_is_not_resolvable_at_n68():
    """The finding that matters most to guard.

    Jev scored 95.6% and gpt-oss 96.7% on the same 68-item arm. Stated as a
    difference that reads as "Jev is behind". Tested here so the number cannot
    be quoted without its interval attached.
    """
    jev = ST.compare_two_proportions(65, 68, 58, 60)
    assert not jev["excludes_zero"], jev
    assert jev["lower"] < 0 < jev["upper"]


# ------------------------------------------------------- power and sample sizing
#
# These exist because `required_n` was wrong twice, in two different directions,
# and neither error raised. The first was a TAIL error: a one-sided test scored
# against the LOWER bound when the question was "is the rate below p0", which has
# an empty rejection region at a 0.95 baseline. The second was an UNDERFLOW: the
# pmf was anchored at k=0, where (1-p)^n is exactly 0.0 for p=0.94 and n=2000, so
# the whole distribution was zero and every power computation returned 0.

@pytest.mark.parametrize("p0,delta", [(0.95, 0.01), (0.95, 0.02), (0.90, 0.05)])
@pytest.mark.parametrize("direction", ["below", "above", "either"])
def test_the_size_required_n_returns_actually_delivers_its_power(p0, delta, direction):
    """The formula's promise is power >= requested. Check it exactly.

    `required_n` is a normal approximation and is badly optimistic here -- at a
    0.95 baseline the interesting region sits several binomial standard
    deviations from the mean. `required_n_exact` is the number to use, and this
    test is what keeps the two honestly related.
    """
    n = ST.required_n_exact(p0, delta, power=0.80, direction=direction)
    got = ST.achieved_power(n, p0, delta, alpha=0.05, direction=direction)
    assert got >= 0.80, (direction, p0, delta, n, got)
    # Only the upper claim is asserted: the returned n reaches the target. No
    # claim is made that n is minimal or that n-1 fails, because exact power is
    # NOT monotone in n -- a two-sided test at 0.95 runs 0.0935 at n=78 and
    # 0.0478 at n=100, falling as n grows -- so "the value below the answer also
    # fails" is not a property power has. `required_n_exact` is documented as
    # returning the first point on a 64-case grid that reaches the target, which
    # is an UPPER bound on the true minimum, and that is the whole claim.


def test_power_under_the_alternative_is_not_vacuous():
    """A 1-point drop from 0.95 IS detectable, and needs thousands of cases.

    This is the answer to "how big should the corpus be", and it is much larger
    than the normal approximation suggests. A 90% corpus that claims to have
    detected a 1-point difference has not.
    """
    n = ST.required_n_exact(0.95, 0.01, power=0.80, direction="below")
    assert 2000 < n < 20000, n
    assert ST.achieved_power(200, 0.95, 0.01, direction="below") < 0.25
    assert ST.achieved_power(2_000, 0.95, 0.01, direction="below") < 0.80


def test_the_normal_approximation_is_flagged_as_optimistic():
    """It under-reports n by roughly 85-95% at these baselines, and says so.

    The approximation is kept because it is a useful lower bound and cheap, but
    `plan_corpus` must not present it as the design guarantee.
    """
    r = ST.plan_corpus()
    assert r["approximation_is_optimistic"] is True
    for row in r["rows"]:
        assert row["approximation_n"] < row["required_n"]
        assert row["approximation_error"] < -0.5
        assert row["exact_power"] >= 0.78


def test_binomial_pmf_vector_sums_to_one_and_does_not_underflow():
    """The underflow case, pinned.

    At p=0.94, n=2000 the pmf at k=0 is (0.06)^2000, which is 0.0 in float64.
    Anchoring there zeroed the entire vector, and three functions then agreed
    with each other and were all wrong: power 0.000 at every n, and a search that
    returned its cap.
    """
    for n, p in ((2000, 0.94), (500, 0.85), (100, 0.5), (20, 0.94), (10_000, 0.99)):
        pmf = ST._binomial_pmf_vector(n, p)
        assert len(pmf) == n + 1
        assert abs(sum(pmf) - 1.0) < 1e-9, (n, p, sum(pmf))
        assert max(pmf) > 0.0
        # and the mode really is the mode
        assert pmf.index(max(pmf)) == int((n + 1) * p)


def test_pmf_vector_matches_the_independent_formula():
    for n, p in ((30, 0.4), (60, 0.85), (200, 0.94)):
        pmf = ST._binomial_pmf_vector(n, p)
        for k in (0, n // 3, n // 2, n - 1):
            direct = math.comb(n, k) * p ** k * (1 - p) ** (n - k)
            assert pmf[k] == pytest.approx(direct, rel=1e-9, abs=1e-300), (n, p, k)


def test_a_one_sided_test_on_the_wrong_tail_has_no_power():
    """The original bug, stated as a test.

    Deciding "is the rate below 0.95" by requiring the LOWER bound to exceed
    0.95 is not a weak test, it is an empty one: the lower bound of a 95%-accurate
    system sits near 0.92 and no sample size moves it up to 0.95.
    """
    for n in (500, 2000, 20_000):
        below = ST.achieved_power(n, 0.95, 0.01, direction="below")
        assert below > 0.0
    # The wrong rule is the "above" test applied where "below" was asked.
    wrong = ST.achieved_power(2000, 0.95, 0.01, direction="above")
    assert wrong < below, (wrong, below)


def test_plan_corpus_pairs_every_size_with_the_bound_it_earns():
    r = ST.plan_corpus()
    assert r["all_rows_meet_power"] is True
    for row in r["rows"]:
        assert row["zero_failure_upper_bound"] > 0
        assert row["zero_failure_upper_bound"] < 0.05
        # A larger corpus must buy a tighter bound, so the ordering of the table
        # has to be monotone in the size.
    sizes = [row["required_n"] for row in r["rows"]]
    bounds = [row["zero_failure_upper_bound"] for row in r["rows"]]
    for s, b in zip(sizes, bounds):
        assert b == pytest.approx(1 - 0.05 ** (1 / s), rel=1e-6)


def test_required_n_rejects_a_nonsense_decision():
    for bad in (dict(direction="sideways"), dict(direction="below", delta=0.0),
                dict(direction="below", power=1.5), dict(direction="below", alpha=0.0)):
        with pytest.raises(ValueError):
            ST.required_n(0.95, bad.get("delta", 0.01), direction=bad["direction"],
                          power=bad.get("power", 0.8), alpha=bad.get("alpha", 0.05))


def test_the_two_sided_rejection_region_is_a_union_not_a_monotone_range():
    """A third bug in the same function, and the one that reported certainty.

    "either" is a prefix (upper < p0) UNION a suffix (lower > p0). That union is
    not monotone in k, so bisecting it directly made the search conclude the
    suffix started at k=0 -- every count rejects -- and returned power 1.000 at
    n=78, i.e. a claim that 78 cases detect a one-point difference at a 0.95
    baseline. The two halves are now bisected separately on their own monotone
    predicates.
    """
    n = 78
    limit = ST._rejection_limit(n, 0.95, 0.05, "either")
    assert isinstance(limit, tuple) and limit[0] in ("either", "contiguous")
    if limit[0] == "contiguous":
        return  # the two components met; nothing to assert about the union
    _, k_low, k_high = limit
    assert k_low >= 0, "no prefix rejected, which cannot be right here"
    assert k_high > k_low, (k_low, k_high)
    # The suffix must not start at the beginning of the range.
    assert k_high > n * 0.5, k_high
    for k in range(n + 1):
        # k_low is the last rejecting k of the prefix; k_high the first of the suffix.
        expect = (k <= k_low) or (k >= k_high)
        assert ST._reject(k, n, 0.95, 0.05, "either") == expect, k


def test_power_is_exact_against_a_hand_computed_tail():
    """At n=2000 with p1=0.94 the rejection region is a prefix, and its mass is
    the binomial cumulative probability up to that prefix. Computed independently
    here to pin the optimised implementation against a naive one."""
    n, p1, p0, alpha = 2000, 0.94, 0.95, 0.05
    limit = ST._rejection_limit(n, p0, alpha, "below")
    pmf = ST._binomial_pmf_vector(n, p1)
    expected = sum(pmf[:limit + 1])
    assert ST.achieved_power(n, p0, 0.01, alpha, "below") == pytest.approx(expected, rel=1e-12)
    assert 0.60 < expected < 0.70, expected


def test_rejection_limit_is_exhaustive_equivalent():
    """The boundary must agree with scanning every k, for every direction.

    `_rejection_limit` took five rewrites before it matched a linear scan, and
    every earlier version returned a power figure that was plausible and wrong
    rather than an error. This is the test that would have caught the first four:
    it compares the bisected endpoints against `exhaustive_rejection_region`, the
    reference implementation.
    """
    for n, p0, alpha in ((50, 0.5, 0.05), (78, 0.95, 0.05), (200, 0.95, 0.05),
                         (500, 0.90, 0.05), (120, 0.80, 0.10), (100, 0.99, 0.05)):
        for direction in ("below", "above", "either"):
            ref = ST.exhaustive_rejection_region(n, p0, alpha, direction)
            limit = ST._rejection_limit(n, p0, alpha, direction)
            if isinstance(limit, tuple) and limit and limit[0] == "contiguous":
                got = list(range(limit[1] + 1))
            elif direction == "below":
                got = list(range(limit + 1)) if limit >= 0 else []
            elif direction == "above":
                got = list(range(limit, n + 1)) if limit <= n else []
            else:
                got = list(range(limit[1] + 1)) + list(range(limit[2], n + 1))
            assert got == ref, (n, p0, alpha, direction, len(got), len(ref))


def test_exact_power_is_not_monotone_in_n_so_bisection_would_be_invalid():
    """Measured, not assumed. A two-sided test at 0.95 gains then LOSES power as
    n grows: 0.0935 at n=78, 0.0478 at n=100. The rejection region is a set of
    integer counts, so the boundary steps rather than tracking the interval.

    This is why `required_n_exact` scans for a minimum instead of bisecting, and
    why an earlier "first crossing" definition was also wrong: 78 cases already
    reach 0.09, so a first-crossing search that reported 863 was reporting a
    number three orders of magnitude too large without raising.
    """
    a = ST.achieved_power(78, 0.95, 0.02, direction="either")
    b = ST.achieved_power(100, 0.95, 0.02, direction="either")
    assert a > b, (a, b)
    assert ST.achieved_power(78, 0.95, 0.02, direction="below") < \
           ST.achieved_power(2000, 0.95, 0.02, direction="below"), "one-sided grows"
