"""Frequentist intervals, power calculations and clustered comparisons.

Exact binomial bounds describe uncertainty for independent binary observations.
For example, zero failures in 60 independent cases gives a one-sided exact 95%
upper bound near 4.87%; 300 independent cases gives a bound near 0.99%.

Related variants share a source cluster. Cluster bootstrap resamples those
groups with their members together, while design-effect helpers estimate the
effective sample size under an explicit intracluster-correlation assumption.
Callers choose the sampling unit and report that assumption with the result.

The numerical routines use Python's standard library.
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

    Coverage is at least the nominal level under the binomial assumptions.
    Returns two-sided bounds and both one-sided bounds. For k = 0 the lower
    bound is zero and the upper bound expresses uncertainty in the failure rate.
    """
    if n <= 0:
        raise ValueError("n_must_be_positive")
    if not 0 <= k <= n:
        raise ValueError("k_out_of_range")
    if not 0.0 < alpha < 1.0:
        raise ValueError("alpha_out_of_range")
    lo = 0.0 if k == 0 else _beta_ppf(alpha / 2.0, k, n - k + 1.0)
    hi = 1.0 if k == n else _beta_ppf(1.0 - alpha / 2.0, k + 1.0, n - k)
    # At k = 0, the one-sided upper bound is 1 - alpha**(1/n).
    one_sided_hi = 1.0 if k == n else _beta_ppf(1.0 - alpha, k + 1.0, n - k)
    # Handle zero-shape boundary cases directly before calling the beta quantile.
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
    """Return an approximate planning size for a difference from baseline p0.

    The alternative is p0-delta for "below" and p0+delta for "above" or "either".
    Alpha and power set the normal-quantile terms. Check the returned size with
    achieved_power, or use required_n_exact for a grid search with exact bounds.
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

    Seed at the mode, floor((n+1)p), then walk outward using adjacent probability
    ratios. This keeps the initial probability large enough for stable arithmetic.
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
    """Reject when the two-sided interval lies wholly above or below p0."""
    ci = clopper_pearson(k, n, alpha=alpha)
    return ci["lower"] > p0 or ci["upper"] < p0


def _rejection_limit(n: int, p0: float, alpha: float, direction: str):
    """Return inclusive rejection boundaries for integer count k.

    One-sided bounds increase with k. Bisection finds the last count in the
    lower tail or the first in the upper tail. The two-sided path scans all
    counts to represent separate or overlapping tails exactly.
    """
    # Each one-sided predicate is monotone. Keep a satisfying endpoint in the
    # bracket and return its inclusive index; tests compare it with a full scan.
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
    # The two-sided result below uses the complete rejection region, including
    # the possibility that its lower and upper tails meet.
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

    # Exhaustive evaluation handles overlapping tails once per count.
    region = exhaustive_rejection_region(n, p0, alpha, "either")
    if not region:
        return ("either", -1, n + 1)
    # Return inclusive tail boundaries at the gap, or one contiguous span.
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

    Tests compare the optimized one-sided search with this direct evaluation
    across directions and parameter combinations.
    """
    if direction == "either":
        return [k for k in range(n + 1) if _reject_either(k, n, p0, alpha)]
    return [k for k in range(n + 1) if _reject(k, n, p0, alpha, direction)]


def achieved_power(n: int, p0: float, delta: float, alpha: float = 0.05,
                   direction: str = "below") -> float:
    """Sum alternative-distribution mass over the exact rejection region.

    One-sided boundaries use bisection; two-sided boundaries use a full scan.
    The probability vector is seeded at its mode for numerical stability.
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
    """Return the first grid size reaching the target exact power, or max_n.

    Integer rejection boundaries make exact power uneven as n grows. Scan in
    steps of grid and report that resolution alongside the achieved power.
    Reaching max_n requires checking whether the target was attained there.
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
    """Report planning sizes alongside their achieved power and interval bounds.

    Each row records its baseline, effect and direction. Callers choose those
    values for their research question; defaults provide example planning cases.
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

    Computed through Clopper-Pearson for both zero and positive failure counts.
    Tests check the zero-failure bounds near 4.87% for n=60 and 0.99% for n=300.
    """
    return clopper_pearson(failures, n, alpha=0.05)["one_sided_upper"]


# --------------------------------------------------------------------- clustering

def cluster_bootstrap(clusters: dict, statistic, *, n_resamples: int = 2000,
                      alpha: float = 0.05, seed: str = "duecare") -> dict:
    """Percentile bootstrap that resamples whole clusters with replacement.

    Each sampled group brings all its per-item records. The caller supplies the
    statistic and grouping appropriate to the study. A fixed seed makes the
    resulting interval reproducible.
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
    grouping field. Returns clustered and naive binomial intervals with their
    width ratio. Interpret that ratio alongside the study's dependence structure
    and the sampling assumptions of each interval method.
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
    """Return mean cluster size under a working correlation assumption of one.

    This computes 1 + (mbar - 1). Outcome-based correlation estimation and
    unequal-size corrections require additional data and a separate estimator.
    """
    if not sizes:
        raise ValueError("no_clusters")
    mbar = sum(sizes) / len(sizes)
    return 1.0 + (mbar - 1.0)


def effective_sample_size(sizes: list) -> float:
    """Divide item count by the working design effect from mean cluster size.

    Under this assumption, 50,000 items in 1,000 groups of 50 yield 1,000.
    The returned count is conditional on the assumption in design_effect.
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
    uses discordant pairs. The report records shared and missing item IDs
    alongside the paired denominator.
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
