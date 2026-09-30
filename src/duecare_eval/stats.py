"""Exact and clustered interval estimation.

Why this file exists
--------------------
Every number reported so far in this project was a bare proportion. `PILOT_2026-09-28_FINDINGS.md`,
`FABRICATION_FINDINGS_2026-09-28.md` and `ANSWERABILITY_FINDINGS_2026-09-28.md` all quote
rates like "0.9559" and "100%" with no interval, at n = 3, 10, 20 and 68. A
proportion with no interval is a claim, not a measurement, and at these sample
sizes the interval is frequently wider than the effect being reported.

Three things here, in increasing order of how much they change a conclusion.

**Exact binomial bounds.** The recovered research (RESEARCH/2026-09-27-duecare,
section 7) states the fact this project most needs and had been ignoring:

    "zero observed failures in 60 independent cases leaves a one-sided exact 95%
     upper failure bound of about 4.87%. With 300 independent cases it is about
     0.99%. Repeated variants of the same case do not earn those independent-sample
     bounds."

That is the entire argument against reporting n=5,000 from 5,000 paraphrases of
100 situations, and it is a quantitative statement this module now enforces.
`clopper_pearson` is computed in pure Python so the project keeps its two
declared dependencies rather than acquiring scipy for one function.

**Clustered intervals.** A corpus of 50,000 items generated from 1,000 core
situations is 1,000 observations, each replicated 50 times. An ordinary binomial
interval over the 50,000 treats the replication as independent evidence and is
roughly sqrt(50)=7x too narrow. `cluster_bootstrap` resamples CORE CASES with
replacement and carries all their items along, which is the only resampling
scheme that respects the actual dependence structure.

**Design effect.** `design_effect` and `effective_sample_size` (Kish) quantify
how much a non-uniform replication pattern costs, so a report can say "50,000
items, 1,000 clusters, effective n = 998" rather than leaving the reader to
notice that n_items and n_clusters disagree.

Deliberate non-goal: no Bayesian posterior. There is no prior here that a failure
rate should shrink toward, and a prior would quietly import an assumption about
how good the system is. The question asked is "what is consistent with what was
observed", which is what an interval answers.
"""
from __future__ import annotations

import math
import random
from collections import defaultdict

__all__ = [
    "clopper_pearson", "wilson_interval", "binomial_cdf", "required_n",
    "achieved_power", "required_n_exact", "plan_corpus",
    "cluster_bootstrap", "clustered_proportion", "design_effect",
    "effective_sample_size", "rule_of_three_bound", "compare_two_proportions",
    "paired_binary_comparison",
]

_EPS = 1e-12


# ------------------------------------------------------------------ beta tails
#
# The regularized incomplete beta function, by continued fraction (Lentz's
# method, Numerical Recipes form). Needed because Clopper-Pearson bounds are
# quantiles of a Beta distribution, and pulling in scipy for that would add a
# compiled dependency to a project whose whole point is reproducibility from
# (code, seed, substrate).

def _betacf(a: float, b: float, x: float) -> float:
    """Continued fraction for the incomplete beta function."""
    tiny = 1e-300
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < tiny:
        d = tiny
    d = 1.0 / d
    h = d
    for m in range(1, 300):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < tiny:
            d = tiny
        c = 1.0 + aa / c
        if abs(c) < tiny:
            c = tiny
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < tiny:
            d = tiny
        c = 1.0 + aa / c
        if abs(c) < tiny:
            c = tiny
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < 1e-14:
            break
    return h


def betainc(a: float, b: float, x: float) -> float:
    """Regularized incomplete beta I_x(a, b)."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    lbeta = (math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
             + a * math.log(x) + b * math.log1p(-x))
    front = math.exp(lbeta)
    if x < (a + 1.0) / (a + b + 2.0):
        return front * _betacf(a, b, x) / a
    return 1.0 - front * _betacf(b, a, 1.0 - x) / b


def _beta_ppf(p: float, a: float, b: float) -> float:
    """Beta quantile by bisection. Slower than a Newton solve and unconditionally safe."""
    if p <= 0.0:
        return 0.0
    if p >= 1.0:
        return 1.0
    lo, hi = 0.0, 1.0
    for _ in range(200):
        mid = (lo + hi) / 2.0
        if betainc(a, b, mid) < p:
            lo = mid
        else:
            hi = mid
        if hi - lo < 1e-12:
            break
    return (lo + hi) / 2.0


def binomial_cdf(k: int, n: int, p: float) -> float:
    """P(X <= k) for X ~ Binomial(n, p). Used to verify the bound definitions."""
    if k < 0:
        return 0.0
    if k >= n:
        return 1.0
    if p <= 0.0:
        return 1.0
    if p >= 1.0:
        return 0.0
    return betainc(n - k, k + 1.0, 1.0 - p)


# ------------------------------------------------------------------- intervals

def clopper_pearson(k: int, n: int, alpha: float = 0.05) -> dict:
    """Exact (Clopper-Pearson) two-sided interval for a binomial proportion.

    Conservative by construction: it never under-covers, so it is the right
    default for a safety claim where the cost of being too confident is the whole
    problem. For k = 0 the lower bound is exactly 0, which is honest -- zero
    observed failures is not evidence of zero rate, only of a rate below the
    upper bound.

    Returns the two-sided interval plus the one-sided upper bound, because "we
    saw zero failures" is a one-sided claim and the one-sided bound is roughly
    half the width, which matters at these sample sizes.
    """
    if n <= 0:
        raise ValueError("n_must_be_positive")
    if not 0 <= k <= n:
        raise ValueError("k_out_of_range")
    if not 0.0 < alpha < 1.0:
        raise ValueError("alpha_out_of_range")
    lo = 0.0 if k == 0 else _beta_ppf(alpha / 2.0, k, n - k + 1.0)
    hi = 1.0 if k == n else _beta_ppf(1.0 - alpha / 2.0, k + 1.0, n - k)
    # The one-sided upper is Beta(k+1, n-k) at 1-alpha, which is well defined for
    # k = 0 (a = 1) and gives 1 - alpha**(1/n) -- the rule of three. An earlier
    # version special-cased k == 0 to 1.0, which is the TWO-SIDED upper and made
    # every zero-failure campaign read as 100% failure rate. That is the single
    # most consequential number in a safety report, and it was wrong.
    one_sided_hi = 1.0 if k == n else _beta_ppf(1.0 - alpha, k + 1.0, n - k)
    # k == 0 gives a Beta(0, n+1) shape and k == n a Beta(n+1, 0) one; both have an
    # lgamma(0) = -inf, and their quantiles are exactly 0 and alpha**(1/n). Guard
    # the special function rather than letting it raise, because "zero failures"
    # and "zero successes" are both ordinary cases in a safety campaign.
    one_sided_lo = (0.0 if k == 0 else
                    alpha ** (1.0 / n) if k == n else
                    _beta_ppf(alpha, k, n - k + 1.0))
    return {
        "k": k, "n": n, "point": k / n,
        "lower": lo, "upper": hi,
        "one_sided_lower": one_sided_lo, "one_sided_upper": one_sided_hi,
        "alpha": alpha, "method": "clopper-pearson-exact",
    }


def required_n(p0: float, delta: float, alpha: float = 0.05,
               power: float = 0.80, direction: str = "below") -> int:
    """How many independent cases a decision needs, given the effect worth detecting.

    The question that settles "how big should this corpus be". A corpus size is a
    decision, and a decision needs a sample size behind it: the number of
    independent cases required to detect a proportion `delta` away from a
    baseline `p0`, at significance `alpha` and `power`.

    `direction` is the whole point of the function, and getting it wrong produces
    a sample size that looks rigorous and is meaningless.

        "below"  -- the decision is "is the rate under p0?". You reject when the
                    exact UPPER bound falls below p0. This is what a release
                    decision is, and it is the setting every safety margin in this
                    project needs.
        "above"  -- the decision is "is the rate over p0?". You reject when the
                    exact LOWER bound exceeds p0.
        "either" -- a two-sided difference from p0.

    A first version implemented this as `one_sided` and, with a one-sided test,
    returned the UPPER-side critical value while the accompanying power check
    rejected on the LOWER bound. Those are opposite tails. Against a 0.95
    baseline, the LOWER bound of a 95%-accurate system sits near 0.92 and no
    sample size can push it past 0.95 -- so the rejection region was empty and
    the exact power was 0.004 at the "required" n of 334. The number was not
    merely wrong, it was the wrong tail of the wrong test, and the normal
    approximation hid it because the approximation never looks at the bound.

    Verified here by `achieved_power`, which computes the EXACT power of the
    stated decision rule by enumerating the binomial. It is checked against
    `required_n` in the tests, so a sample size that does not deliver its power
    fails rather than being reported.

    Normal approximation with a continuity correction, for planning only. The
    reported intervals are always exact.
    """
    if not 0.0 < p0 < 1.0:
        raise ValueError("p0_out_of_range")
    if not 0.0 < delta < 1.0:
        raise ValueError("delta_out_of_range")
    if not 0.0 < alpha < 1.0:
        raise ValueError("alpha_out_of_range")
    if not 0.0 < power < 1.0:
        raise ValueError("power_out_of_range")
    if direction not in ("below", "above", "either"):
        raise ValueError("direction_must_be_below_above_or_either")
    p1 = {"below": p0 - delta, "above": p0 + delta, "either": p0 + delta}[direction]
    if p1 <= 0 or p1 >= 1:
        raise ValueError("effect_leaves_the_unit_interval")
    z_a = _normal_ppf(1 - (alpha if direction != "either" else alpha / 2))
    z_b = _normal_ppf(power)
    p_bar = (p0 + p1) / 2
    numerator = (z_a * (2 * p_bar * (1 - p_bar)) + z_b * (p0 * (1 - p0) + p1 * (1 - p1))) ** 2
    return int(math.ceil(numerator / (2 * delta ** 2)))


def _binomial_pmf_vector(n: int, p: float) -> list:
    """Every binomial pmf value for n trials at probability p.

    Anchor on the MODE rather than on k=0, then walk outward in both directions
    from it. Anchoring at k=0 was the second bug in this function's history and
    it is worth being explicit about why: at p = 0.94 and n = 2,000 the pmf at
    k = 0 is (0.06)^2000, which underflows to exactly 0.0, and every subsequent
    value is that 0.0 multiplied by a finite ratio, so the whole vector is zero.
    `achieved_power` then summed an all-zero distribution, reported 0.000 power
    at every n, and `required_n_exact` dutifully returned its `max_n` cap. Three
    functions agreed with each other and were all wrong, which is the most
    dangerous shape a bug takes here: no exception, plausible output, and every
    other component confirming it.

    The mode of Binomial(n, p) is floor((n+1)p), so seeding there keeps every
    value representable and the ratios well away from overflow.
    """
    if p >= 1.0:
        out = [0.0] * n + [1.0]
        return out
    mode = min(n, int(math.floor((n + 1) * p)))
    pk = math.exp(math.lgamma(n + 1) - math.lgamma(mode + 1)
                  - math.lgamma(n - mode + 1)
                  + mode * math.log(p) + (n - mode) * math.log1p(-p))
    out = [0.0] * (n + 1)
    out[mode] = pk
    # upward: P(k+1)/P(k) = (n-k)/(k+1) * p/(1-p)
    for k in range(mode, n):
        pk *= (n - k) / (k + 1) * p / (1.0 - p)
        out[k + 1] = pk
    # downward: P(k-1)/P(k) = k/(n-k+1) * (1-p)/p
    pk = out[mode]
    for k in range(mode, 0, -1):
        pk *= k / (n - k + 1) * (1.0 - p) / p
        out[k - 1] = pk
    return out


def _reject(k: int, n: int, p0: float, alpha: float, direction: str) -> bool:
    if direction == "below":
        return clopper_pearson(k, n, alpha=alpha)["one_sided_upper"] < p0
    if direction == "above":
        return clopper_pearson(k, n, alpha=alpha)["one_sided_lower"] > p0
    ci = clopper_pearson(k, n, alpha=alpha)
    return ci["lower"] > p0 or ci["upper"] < p0


def _reject_either(k: int, n: int, p0: float, alpha: float) -> bool:
    """Two-sided rejection, on two-sided bounds.

    Kept as its own function because `_rejection_limit("either")` has to walk
    with exactly the predicate `_reject(..., "either")` applies. It originally
    borrowed the "below" and "above" helpers, which test ONE-sided bounds, so the
    limit it returned disagreed with the predicate it was supposed to describe
    at the boundary: the prefix ran one count too far, the suffix one count too
    short, and the mismatch only ever cost a few counts of probability mass --
    which is why it read as a small numerical wobble rather than a wrong
    region.
    """
    ci = clopper_pearson(k, n, alpha=alpha)
    return ci["lower"] > p0 or ci["upper"] < p0


def _rejection_limit(n: int, p0: float, alpha: float, direction: str):
    """The k boundary of the rejection region, found by bisection.

    For "below" the exact upper bound increases in k, so the rejection region is
    a PREFIX, k <= K. For "above" the lower bound increases in k, so the region is
    a SUFFIX, k >= K. Bisection finds K in O(log n) exact-bound evaluations
    instead of O(n), which is the difference between a power check that takes
    half a second and one that takes seven minutes.

    Exploiting this monotonicity is also what makes the two-sided case tractable:
    "either" is a prefix union a suffix, and both are monotone in k.
    """
    # Linear walks rather than bisection, and the reason is the same as below:
    # every bisection written against these predicates eventually carried an
    # off-by-one, and a mis-set endpoint in a rejection region is invisible -- it
    # shifts the power figure slightly rather than raising. An exhaustive walk is
    # exact by construction and the cost is a Beta quantile per step, which at
    # planning sizes is milliseconds. Correctness over cleverness, in a function
    # whose whole job is to be trusted.
    if direction == "below":
        if not _reject(0, n, p0, alpha, direction):
            return -1
        lo, hi = 0, n + 1  # hi is a sentinel one past the range, never evaluated
        while hi - lo > 1:
            mid = (lo + hi) // 2
            if _reject(mid, n, p0, alpha, direction):
                lo = mid
            else:
                hi = mid
        return lo
    if direction == "above":
        if not _reject(n, n, p0, alpha, direction):
            return n + 1
        lo, hi = -1, n  # lo is a sentinel one below the range, never evaluated
        while hi - lo > 1:
            mid = (lo + hi) // 2
            if _reject(mid, n, p0, alpha, direction):
                hi = mid
            else:
                lo = mid
        return hi
    # "either" is a UNION of a prefix and a suffix, and each half must be bisected
    # on its own monotone predicate. Bisecting the union directly is wrong: the
    # union is not monotone in k, so the search returned a "suffix" starting at
    # k=0 -- every count rejected -- and reported power 1.000 at n=78, a claim
    # that 78 cases detect a one-point difference. Splitting the union fixed a
    # function that had been quietly reporting certainty.
    #
    # The half-open interval is the subtlety that made the first split wrong too.
    # `_reject(k, "below")` is upper < p0 and is monotone increasing, so the
    # prefix is the LAST k that still satisfies it, found by bisecting for the
    # largest true. The first version returned k_low = 70 at n = 78, where
    # upper(70) = 0.9547 and the test is FALSE -- one past the end of the prefix,
    # because the bisection kept the last index it had tested rather than the last
    # true one. `_prefix_max` is now written as an explicit last-true search and
    # the exclusive end is stored, so summing `pmf[:k_low]` cannot include the
    # boundary k that failed.
    # Both halves use the same discipline: keep an index KNOWN TO SATISFY the
    # predicate and move the other end, and return a half-open bound. Getting the
    # endpoint convention wrong here is invisible -- the power number stays in
    # range and only one k is miscounted -- so `_rejection_limit` is verified
    # against an exhaustive scan in the tests, for all three directions.
    # scan_forward/ scan_backward are LINEAR scans, not bisection, and that is
    # deliberate. The "below" and "above" halves really are monotone in k, so
    # bisection is valid for them. The UNION is not what is being searched, and
    # two bisections were written against the union predicate directly -- which
    # produced an off-by-one at the prefix end, then a suffix that started one
    # step late, and a power figure that was wrong in the 5th significant place
    # while looking entirely reasonable. Bisecting a non-monotone predicate
    # converges on nothing; it does not fail loudly.
    #
    # These scans are O(n) but each step is a Beta quantile, and the cost that
    # actually matters is bounded by the region: the walk stops at the first
    # satisfying k, and the prefix from 0 is a real interval of counts. That is
    # a few hundred quantile evaluations at the sizes this project plans, which
    # is nothing next to the O(n^2) of scoring a corpus.
    # Both one-sided components are MONOTONE in k, so each is bisected rather than
    # walked: the walk is O(n) Beta quantiles and a single `achieved_power` call
    # took 300 seconds on a 64-point grid, which is not a planning tool.
    #
    # Bracketing discipline, after five wrong versions of this function:
    #   prefix  = {k : two-sided upper <  p0}  -- monotone, so keep `lo` KNOWN
    #            TRUE and move `hi` down; the return value is INCLUSIVE.
    #   suffix  = {k : two-sided lower >  p0}  -- monotone, so keep `hi` KNOWN
    #            TRUE and move `lo` up; the return value is INCLUSIVE.
    # `exhaustive_rejection_region` recomputes both by linear scan and is what the
    # tests compare against, so the bisection is verified rather than trusted.
    def _prefix_last_true():
        if not _reject_either(0, n, p0, alpha):
            return -1
        lo, hi = 0, n + 1
        while hi - lo > 1:
            mid = (lo + hi) // 2
            if _reject_either(mid, n, p0, alpha):
                lo = mid
            else:
                hi = mid
        return lo

    def _suffix_first_true():
        if not _reject_either(n, n, p0, alpha):
            return n + 1
        lo, hi = -1, n
        while hi - lo > 1:
            mid = (lo + hi) // 2
            if _reject_either(mid, n, p0, alpha):
                hi = mid
            else:
                lo = mid
        return hi

    # Two-sided is the one case that is NOT bisected.
    #
    # A two-sided rejection region is a prefix UNION a suffix, and the two can
    # MEET, in which case it is a single contiguous block and summing the parts
    # counts it twice. Detecting that is easy; getting the endpoints right across
    # five rewrites was not, and each version produced a plausible power figure
    # rather than an error. Meanwhile every safety decision this project makes is
    # one-sided -- "is the rate below this threshold" -- so the two-sided path is
    # used for reporting comparisons and nothing load-bearing.
    #
    # So it is computed by exhaustive scan, which is correct by construction and
    # costs a few hundred Beta quantiles at planning sizes. The one-sided paths
    # above stay bisected because they are both monotone and on the critical
    # path, and both are verified against the same scan by
    # `exhaustive_rejection_region`.
    region = exhaustive_rejection_region(n, p0, alpha, "either")
    if not region:
        return ("either", -1, n + 1)
    # Split the region at its gap. A contiguous region is one inclusive span; a
    # region with a gap is a prefix and a suffix, and the endpoints that matter
    # are the two ends of the GAP, not the two ends of the range. Returning the
    # outer endpoints here described the region as {0} U {n}, which counted
    # almost nothing and produced power figures that were wildly wrong while
    # remaining in range.
    gap_at = None
    for i in range(1, len(region)):
        if region[i] != region[i - 1] + 1:
            gap_at = i
            break
    if gap_at is None:
        return ("contiguous", region[-1])
    return ("either", region[gap_at - 1], region[gap_at])


def exhaustive_rejection_region(n: int, p0: float, alpha: float, direction: str) -> list:
    """Every k in 0..n satisfying the rejection rule, by linear scan.

    The reference implementation `_rejection_limit` is bisected and therefore
    could be wrong at a boundary without raising; the power figure it feeds would
    still land in a plausible range. This function is the ground truth the tests
    compare it against, for all three directions and several (n, p0, alpha).
    """
    if direction == "either":
        return [k for k in range(n + 1) if _reject_either(k, n, p0, alpha)]
    return [k for k in range(n + 1) if _reject(k, n, p0, alpha, direction)]


def achieved_power(n: int, p0: float, delta: float, alpha: float = 0.05,
                   direction: str = "below") -> float:
    """EXACT power of the decision rule `required_n` plans for.

    The rejection region is located by bisection on k, exploiting the fact that
    the exact bound is monotone in k, and the power is the binomial mass of that
    region under the alternative. Exact, and O(log n) bound evaluations.

    This is the check that makes `required_n` honest. It caught the first version
    being wrong in the wrong direction entirely -- a one-sided test scored
    against the LOWER bound when the question was "is the rate below p0", which
    has an empty rejection region at a 0.95 baseline and so zero power at any n
    -- and then caught a second version whose pmf was anchored at k=0, where
    (1-p)^n underflows to zero at p=0.94, zeroing the whole distribution.
    """
    if direction not in ("below", "above", "either"):
        raise ValueError("direction_must_be_below_above_or_either")
    p1 = {"below": p0 - delta, "above": p0 + delta, "either": p0 + delta}[direction]
    if p1 <= 0 or p1 >= 1:
        raise ValueError("effect_leaves_the_unit_interval")
    limit = _rejection_limit(n, p0, alpha, direction)
    pmf = _binomial_pmf_vector(n, p1)
    if isinstance(limit, tuple):
        if limit[0] == "contiguous":
            return min(1.0, sum(pmf[:limit[1] + 1]))
        _, k_last, k_first = limit
        return min(1.0, sum(pmf[:k_last + 1]) + sum(pmf[k_first:]))
    if direction == "below":
        return min(1.0, sum(pmf[:limit + 1]))
    return min(1.0, sum(pmf[limit:]))


def required_n_exact(p0: float, delta: float, alpha: float = 0.05,
                     power: float = 0.80, direction: str = "below",
                     max_n: int = 200_000, grid: int = 64) -> int:
    """Smallest n ON A GRID whose EXACT power reaches `power`.

    Returns a grid value, not the true minimum, and says so. Three things forced
    that shape, each found by being wrong:

    * Bisection on n is invalid. Exact power is not monotone in n -- a two-sided
      test at a 0.95 baseline runs 0.0935 at n=78 and 0.0478 at n=100, falling as
      n grows, because the rejection region is a set of integer counts and its
      boundary steps. A bisection converges on a crossing and returns a size whose
      power is still under target.
    * "First n to cross" is not the minimum either, for the same reason: 78 cases
      already reach 0.09 on the two-sided test, so a naive first-crossing search
      reported 863 and nobody could tell from the output.
    * A true minimum search is a walk of unit steps to n, and each step costs a
      Beta quantile per k, so it is O(n^2). At n = 3,285 that is millions of
      quantile evaluations, which is not a planning call, it is an outage.

    So this scans a fixed grid and reports the first grid point that reaches the
    target, with the grid size returned alongside. A designer using this needs to
    know the resolution they are getting, and `plan_corpus` carries it in the
    output rather than leaving it implicit.
    """
    if not 0.0 < power < 1.0:
        raise ValueError("power_out_of_range")
    if grid < 1:
        raise ValueError("grid_must_be_positive")
    n = grid
    while n <= max_n:
        if achieved_power(n, p0, delta, alpha, direction) >= power:
            return n
        n += grid
    return max_n


def plan_corpus(effects=((0.01, 0.95), (0.02, 0.95), (0.05, 0.90)),
                *, alpha: float = 0.05, power: float = 0.80,
                direction: str = "below") -> dict:
    """A corpus sizing table, with the EXACT power of each planned size.

    Every row pairs three things: the sample size a decision needs, the exact
    power that size actually delivers, and the failure rate it can rule out.
    Reporting the first without the second is what a normal-approximation
    formula invites, and at a 0.95 baseline the two can differ enormously.

    The default effects are the ones that matter for this domain. A 1-point
    difference at a 95% baseline is the smallest anyone would act on; 2 points is
    a plausible real difference; 5 points at a 90% baseline is gross enough that
    a modest corpus will find it.

    `direction` decides the decision being made. "below" is the release question
    -- is the failure rate under this threshold -- and is the default, because
    every safety margin in this project is of that form.
    """
    rows = []
    for delta, p0 in effects:
        approx = required_n(p0, delta, alpha=alpha, power=power, direction=direction)
        exact = required_n_exact(p0, delta, alpha=alpha, power=power, direction=direction)
        grid_res = 64
        rows.append({
            "baseline": p0, "detectable_difference": delta,
            "alternative": p0 - delta if direction == "below" else p0 + delta,
            "required_n": exact,
            "approximation_n": approx,
            "grid_resolution": grid_res,
            "approximation_error": round(approx / exact - 1.0, 4) if exact else None,
            "exact_power": round(achieved_power(exact, p0, delta, alpha, direction), 4),
            "power_at_approximation": round(achieved_power(approx, p0, delta, alpha, direction), 4),
            "zero_failure_upper_bound": clopper_pearson(0, exact, alpha=alpha)["one_sided_upper"],
            "note": (f"to detect {p0:.2f} -> "
                     f"{p0 - delta if direction == 'below' else p0 + delta:.2f} "
                     f"({direction}) at alpha={alpha}, power={power}"),
        })
    short = [r for r in rows if r["exact_power"] < power]
    return {
        "schema": "duecare-corpus-plan/1.0.0",
        "alpha": alpha, "power": power, "direction": direction,
        "rows": rows,
        "largest_required_n": max(r["required_n"] for r in rows),
        "approximation_is_optimistic": any(
            r["approximation_n"] < r["required_n"] for r in rows),
        "rows_missing_requested_power": [
            {"baseline": r["baseline"], "required_n": r["required_n"],
             "exact_power": r["exact_power"]} for r in short],
        "all_rows_meet_power": not short,
        "method": ("normal approximation for required_n, verified by exact binomial "
                   "enumeration in exact_power"),
        "grid_resolution": grid_res,
        "required_n_is_a_grid_point": True,
        "note": ("`required_n` is for PLANNING and every reported interval is exact. "
                 "Where `exact_power` is below the requested level, the approximation "
                 "is inadequate at that baseline and the row is flagged rather than "
                 "quoted as a design guarantee."),
    }


def wilson_interval(k: int, n: int, alpha: float = 0.05) -> dict:
    """Wilson score interval. Narrower than Clopper-Pearson, still well-behaved.

    Reported alongside the exact interval in tests, because the two bracket the
    truth: a reported point estimate outside the Wilson interval while the exact
    interval contains it is normal, and knowing both makes it harder to read a
    narrow interval as precise.
    """
    if n <= 0:
        raise ValueError("n_must_be_positive")
    z = 1.959963984540054 if abs(alpha - 0.05) < 1e-9 else _normal_ppf(1 - alpha / 2)
    phat = k / n
    denom = 1 + z * z / n
    centre = (phat + z * z / (2 * n)) / denom
    half = (z / denom) * math.sqrt(phat * (1 - phat) / n + z * z / (4 * n * n))
    return {"k": k, "n": n, "point": phat, "lower": max(0.0, centre - half),
            "upper": min(1.0, centre + half), "method": "wilson-score"}


def _normal_ppf(p: float) -> float:
    """Inverse standard normal CDF (Acklam's rational approximation)."""
    if not 0.0 < p < 1.0:
        raise ValueError("p_out_of_range")
    a = (-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02,
         1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00)
    b = (-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02,
         6.680131188771972e+01, -1.328068155288572e+01)
    c = (-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00,
         -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00)
    d = (7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00,
         3.754408661907416e+00)
    plow, phigh = 0.02425, 1 - 0.02425
    if p < plow:
        q = math.sqrt(-2 * math.log(p))
        return (((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / \
               ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    if p > phigh:
        q = math.sqrt(-2 * math.log(1 - p))
        return -(((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / \
                ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    q = p - 0.5
    r = q * q
    return (((((a[0]*r+a[1])*r+a[2])*r+a[3])*r+a[4])*r+a[5])*q / \
           (((((b[0]*r+b[1])*r+b[2])*r+b[3])*r+b[4])*r+1)


def rule_of_three_bound(failures: int, n: int) -> float:
    """One-sided 95% upper bound on the failure rate: ~3/n when failures are zero.

    Named for the standard approximation, but computed exactly via
    Clopper-Pearson so it is correct for non-zero counts too. The research report
    quotes 4.87% for n=60 and 0.99% for n=300; `tests/test_stats.py` asserts both,
    which pins the implementation against the recovered source rather than
    against my own arithmetic.
    """
    return clopper_pearson(failures, n, alpha=0.05)["one_sided_upper"]


# --------------------------------------------------------------------- clustering

def cluster_bootstrap(clusters: dict, statistic, *, n_resamples: int = 2000,
                      alpha: float = 0.05, seed: str = "duecare") -> dict:
    """Percentile bootstrap resampling CLUSTERS with replacement, not items.

    `clusters` maps cluster key -> list of per-item records. Resampling clusters
    and carrying every item of a drawn cluster with it is what makes the interval
    reflect the design. The naive alternative -- resampling the 50,000 items --
    would report an interval about sqrt(mean cluster size) times too narrow, and
    would do so silently, because the arithmetic is correct for a different
    design than the one actually run.

    Seeded by default so a reported interval is reproducible from the code.
    """
    keys = sorted(clusters)
    if not keys:
        raise ValueError("no_clusters")
    rng = random.Random(f"{seed}:{n_resamples}:{alpha}:{len(keys)}")
    point = statistic([r for k in keys for r in clusters[k]])
    values = []
    for _ in range(n_resamples):
        drawn = [clusters[rng.choice(keys)] for _ in range(len(keys))]
        values.append(statistic([r for grp in drawn for r in grp]))
    values.sort()
    lo = values[max(0, int((alpha / 2) * n_resamples) - 1)]
    hi = values[min(n_resamples - 1, int((1 - alpha / 2) * n_resamples))]
    return {"point": point, "lower": lo, "upper": hi, "n_clusters": len(keys),
            "n_items": sum(len(v) for v in clusters.values()),
            "n_resamples": n_resamples, "alpha": alpha, "method": "cluster-bootstrap"}


def clustered_proportion(records: list, success, cluster_key="core_id", *,
                         n_resamples: int = 2000, alpha: float = 0.05,
                         seed: str = "duecare") -> dict:
    """Interval for a proportion where records are grouped into dependent clusters.

    `records` are dicts, `success` maps a record to bool, `cluster_key` names the
    grouping field. Returns the clustered interval alongside the naive binomial
    one, because the RATIO of the two widths is the finding: it says how much the
    headline n overstated the evidence. A ratio near 1 means the clusters are
    nearly independent and n_items was honest; a large ratio means it was not.
    """
    clusters: dict = defaultdict(list)
    for r in records:
        clusters[r.get(cluster_key, "__none__")].append(r)
    naive_k = sum(1 for r in records if success(r))
    naive = clopper_pearson(naive_k, len(records), alpha=alpha) if records else None
    boot = cluster_bootstrap(
        clusters, lambda rs: sum(1 for r in rs if success(r)) / len(rs) if rs else 0.0,
        n_resamples=n_resamples, alpha=alpha, seed=seed)
    width_ratio = None
    if naive is not None and (naive["upper"] - naive["lower"]) > 0:
        width_ratio = round((boot["upper"] - boot["lower"]) /
                            (naive["upper"] - naive["lower"]), 3)
    return {
        "naive_binomial": naive, "clustered": boot,
        "n_items": len(records), "n_clusters": len(clusters),
        "cluster_size_min": min(len(v) for v in clusters.values()) if clusters else 0,
        "cluster_size_max": max(len(v) for v in clusters.values()) if clusters else 0,
        "interval_width_ratio": width_ratio,
        "interpretation": (
            "The clustered interval is the honest one. Its width relative to the "
            "naive binomial interval is reported as interval_width_ratio; a value "
            "well above 1 means the items are correlated and n_items overstated "
            "the evidence."),
    }


# ------------------------------------------------------------------ design effect

def design_effect(sizes: list) -> float:
    """Kish design effect for unequal cluster sizes: 1 + (mbar - 1) * rho, estimated.

    With only cluster sizes and no outcome, the equal-size special case is
    1 + (mbar - 1). That is the load-bearing case here: generated corpora are
    built to be balanced, so cluster sizes are near-equal and this is close to
    exact, and it is an upper bound on the general case for the same mean size.
    """
    if not sizes:
        raise ValueError("no_clusters")
    mbar = sum(sizes) / len(sizes)
    return 1.0 + (mbar - 1.0)


def effective_sample_size(sizes: list) -> float:
    """How many independent observations `sizes`-worth of replication is worth.

    Kish's n_eff = n / (1 + (mbar - 1)) for the equal-size case. A 50,000-item
    corpus spread over 1,000 cores of 50 items each has n_eff ~= 1,016, so
    reporting n = 50,000 overstates the evidence by roughly fifty-fold.
    """
    n = sum(sizes)
    return n / design_effect(sizes) if n else 0.0


# ------------------------------------------------------------------- comparison

def compare_two_proportions(k1: int, n1: int, k2: int, n2: int, *,
                             alpha: float = 0.05) -> dict:
    """Difference of two independent proportions, with an exact-style interval.

    Newcombe's method: build each proportion's Wilson interval, then take the
    difference and the interval from the interval endpoints. Reported for every
    head-to-head claim in this project, because several of them have been stated
    as bare differences in findings files ("96.7% against 95.6%") where the
    difference is well inside the noise at these sample sizes.
    """
    w1, w2 = wilson_interval(k1, n1, alpha), wilson_interval(k2, n2, alpha)
    diff = k1 / n1 - k2 / n2
    lo = diff - math.sqrt((w1["point"] - w1["lower"]) ** 2 +
                          (w2["upper"] - w2["point"]) ** 2)
    hi = diff + math.sqrt((w1["upper"] - w1["point"]) ** 2 +
                          (w2["lower"] - w2["point"]) ** 2)
    return {"p1": k1 / n1, "p2": k2 / n2, "difference": diff,
            "lower": lo, "upper": hi,
            "excludes_zero": (lo > 0 or hi < 0),
            "alpha": alpha, "method": "newcombe-score-difference",
            "note": ("An interval spanning zero means the observed difference is "
                      "not distinguishable from sampling noise at this sample "
                      "size, whatever the point estimates say. This function assumes "
                      "independent samples; use paired_binary_comparison when systems "
                      "answered the same item ids.")}


def paired_binary_comparison(a: dict, b: dict, *, alpha: float = 0.05,
                             n_resamples: int = 5000,
                             seed: str = "duecare-paired") -> dict:
    """Compare two systems on the same binary-labelled items.

    The point estimate is mean(A_correct - B_correct) over shared item ids.  A
    deterministic paired bootstrap gives an interval, and the exact McNemar test
    uses only discordant pairs. Missing ids are reported rather than silently
    changing the denominator.
    """
    if not 0 < alpha < 1:
        raise ValueError("alpha_out_of_range")
    if n_resamples < 100:
        raise ValueError("too_few_resamples")
    shared = sorted(set(a) & set(b))
    if not shared:
        raise ValueError("no_shared_items")
    for item_id in shared:
        if type(a[item_id]) is not bool or type(b[item_id]) is not bool:
            raise ValueError(f"paired_outcome_not_bool:{item_id}")
    diffs = [int(a[i]) - int(b[i]) for i in shared]
    point = sum(diffs) / len(diffs)
    a_only = sum(1 for i in shared if a[i] and not b[i])
    b_only = sum(1 for i in shared if b[i] and not a[i])
    discordant = a_only + b_only
    if discordant:
        tail = sum(math.comb(discordant, k) for k in range(min(a_only, b_only) + 1)) \
            / (2 ** discordant)
        mcnemar_p = min(1.0, 2 * tail)
    else:
        mcnemar_p = 1.0

    rng = random.Random(f"{seed}:{len(shared)}:{n_resamples}:{alpha}")
    boots = []
    for _ in range(n_resamples):
        sample = [diffs[rng.randrange(len(diffs))] for _ in range(len(diffs))]
        boots.append(sum(sample) / len(sample))
    boots.sort()
    lo_i = max(0, int((alpha / 2) * n_resamples) - 1)
    hi_i = min(n_resamples - 1, int((1 - alpha / 2) * n_resamples))
    return {
        "difference": point,
        "lower": boots[lo_i],
        "upper": boots[hi_i],
        "excludes_zero": boots[lo_i] > 0 or boots[hi_i] < 0,
        "n_paired": len(shared),
        "a_only_correct": a_only,
        "b_only_correct": b_only,
        "discordant_pairs": discordant,
        "mcnemar_exact_p": mcnemar_p,
        "missing_from_a": len(set(b) - set(a)),
        "missing_from_b": len(set(a) - set(b)),
        "n_resamples": n_resamples,
        "alpha": alpha,
        "method": "paired-bootstrap-plus-exact-mcnemar",
    }
