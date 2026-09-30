"""Multi-judge benchmarking panel: the apparatus, not the oracle.

What a benchmark needs that a scorer does not
---------------------------------------------
A scorer answers "what did this model output on item X". A benchmark answers
"is system A better than system B, and how confident may a reader be in that".
The second question needs machinery that does not exist anywhere in this
project yet:

* **A panel.** Every judge must see the SAME items under the SAME protocol. As of
  this writing every run in `runs/` has exactly ONE judge, so no agreement
  statistic has ever been computable and no judge has ever been checked against
  another. A single judge is an anecdote with a confidence interval.
* **Agreement without ground truth.** Krippendorff's alpha and Fleiss' kappa
  quantify how reliably raters agree using only their mutual agreement, so judge
  quality can be assessed BEFORE any label exists. This is the only judge-quality
  metric available with no adjudicators, which is why it is primary here.
* **Latent truth by consensus.** With several noisy judges, Dawid-Skene style
  error-correcting consensus estimates a label better than any single judge,
  weighting each judge by observed competence. This is what replaces a perfect
  oracle: not a better oracle, but many mediocre ones plus a principled
  aggregation.
* **Honest denominators.** Every metric carries its n, its coverage, and the
  label basis. A comparison that silently drops 60% of items is not a comparison.

What this is not
----------------
This does not claim any system is trustworthy. It measures the judges so the
measurements can be weighed. Disagreement is reported, not averaged away: a
panel that splits on an item is flagging that item for review, and hiding that
behind a mean is how benchmarks end up confidently wrong.
"""

from __future__ import annotations

import math
import statistics
from collections import Counter, defaultdict

from .contracts import canonical, sha

PANEL_PROTOCOL = "judge-panel/2.0.0"
# Label bases, ordered by decreasing strength. A comparison is only meaningful
# within a basis; mixing them silently is the single easiest way to publish a
# wrong table.
BASIS_TIER = "requested_generation_tier"  # circular: the generator's intent
BASIS_ORACLE = "evidence_derived_proposition"  # deterministic, auditable
BASIS_CONSENSUS = "judge_consensus"  # Dawid-Skene over the panel


# ---------------------------------------------------------------- agreement


def _matrix(items: list, judges: list, cell) -> dict:
    """item x judge table of usable ratings. A cell is None when the judge
    abstained, errored or ran out of budget, and those are counted as missing
    rather than as disagreement."""
    out = {}
    for item in items:
        row = {}
        for j in judges:
            try:
                row[j] = cell(item, j)
            except Exception:
                row[j] = None
        out[item] = row
    return out


def ordinal_matrix(records: list) -> dict:
    """Keep each candidate, arm and judging regime as a separate rating unit."""
    table = defaultdict(dict)
    for r in records:
        if r.get("status") != "graded" or r.get("grade") is None:
            continue
        unit = r["item_id"]
        if any(
            r.get(k) is not None for k in ("candidate_model", "candidate_arm", "regime")
        ):
            unit = canonical(
                [
                    unit,
                    r.get("candidate_model"),
                    r.get("candidate_arm"),
                    r.get("regime"),
                ]
            )
        if r["judge"] in table[unit]:
            raise ValueError(
                "duplicate_panel_rating: aggregate repeats before agreement"
            )
        table[unit][r["judge"]] = r["grade"]
    return dict(table)


def _ordinal_distance(rng: list) -> dict:
    """Squared distance on RANKS, not on grade values.

    Grade 1 vs 5 must be the largest gap, and 1 vs 2 a small one, but the gap
    4->5 must not be 5x the gap 1->2 merely because the numbers differ. Ranks
    give the ordering without inventing a magnitude, which is what a 1-5 rubric
    actually licenses.
    """
    index = {v: i for i, v in enumerate(rng)}
    n = len(rng)
    return {
        (index[a], index[b]): ((index[a] - index[b]) / (n - 1)) ** 2 if n > 1 else 0.0
        for a in rng
        for b in rng
    }


def krippendorff_alpha(table: dict, value_range=None) -> float | None:
    """Ordinal Krippendorff's alpha over an item x judge table with missing cells.

    Nominal/interval alpha is wrong for a 1-5 scale: treating grades 1 and 5 as
    maximally distant is correct, but 1 and 2 are NOT maximally distant, and the
    nominal form cannot see that. The ordinal form uses the distance actually
    present in the data.

    Works on the coincidence-matrix formulation, which is what allows the
    item x judge grid to have unequal and missing entries - unavoidable when
    judges abstain or run out of budget.
    """
    units = []
    for row in table.values():
        vals = [v for v in row.values() if v is not None]
        if len(vals) >= 2:
            units.append(vals)
    if len(units) < 2:
        return None
    rng = value_range or sorted({v for vals in units for v in vals})
    if len(rng) < 2:
        return None
    index = {v: i for i, v in enumerate(rng)}

    coincidence = defaultdict(float)
    total = 0.0
    for vals in units:
        n = len(vals)
        for i, a in enumerate(vals):
            for j, b in enumerate(vals):
                if i == j:
                    continue
                w = 1.0 / (n - 1)
                coincidence[(index[a], index[b])] += w
                total += w
    if total <= 0:
        return None
    marg = defaultdict(float)
    for (a, b), v in coincidence.items():
        marg[a] += v

    # Ordinal distance uses cumulative marginal mass between categories, not
    # squared numeric grade differences (which would be interval alpha).
    dist = {}
    for a in marg:
        for b in marg:
            low, high = sorted((a, b))
            mass = sum(marg.get(k, 0.0) for k in range(low, high + 1))
            dist[a, b] = (mass - (marg[a] + marg[b]) / 2.0) ** 2
    do = sum(v * dist[(a, b)] for (a, b), v in coincidence.items()) / total
    de = sum(marg[a] * marg[b] * dist[(a, b)] for a in marg for b in marg) / (
        total * (total - 1)
    )
    if de <= 0:
        return None
    return max(-1.0, min(1.0, 1.0 - (do / de)))


def fleiss_kappa(table: dict, categories=None) -> float | None:
    """Fleiss' kappa with variable raters per item, which is the honest form
    when judges abstain on different items.

    kappa corrects for chance agreement, so a judge that always answers 3 can
    show high raw agreement and zero kappa. Reporting raw agreement alone would
    reward a useless constant judge.
    """
    rows = []
    for row in table.values():
        vals = [v for v in row.values() if v is not None]
        if len(vals) >= 2:
            rows.append(vals)
    if len(rows) < 2:
        return None
    cats = categories or sorted({v for vals in rows for v in vals})
    cidx = {c: i for i, c in enumerate(cats)}
    k = len(cats)
    # Each item's agreement is the fraction of ordered rater pairs that match.
    # With missing raters this is an explicitly item-weighted generalization.
    p_bar_num = 0.0
    for vals in rows:
        n = len(vals)
        counts = Counter(vals)
        same = sum(c * c for c in counts.values())
        p_bar_num += (same - n) / (n * (n - 1))
    p_bar = p_bar_num / len(rows)
    # Nominal kappa ignores the size of a disagreement; independence should
    # nevertheless give zero. The old missing factor n produced false agreement.
    total_ratings = sum(len(v) for v in rows)
    if total_ratings == 0:
        return None
    overall = Counter(v for vals in rows for v in vals)
    p_e = sum((overall.get(c, 0) / total_ratings) ** 2 for c in cats)
    if p_e >= 1.0:
        return None
    return max(-1.0, min(1.0, (p_bar - p_e) / (1.0 - p_e)))


def weighted_kappa(table: dict, categories=None) -> float | None:
    """Quadratic-weighted kappa: closer to Krippendorff ordinal, useful as a
    cross-check when the two disagree materially. Weights are on RANKS, so the
    value is bounded by 1; weighting raw grade values let it exceed 1, which is
    not a real value and would silently corrupt any ranking built on it."""
    rows = [[v for v in row.values() if v is not None] for row in table.values()]
    rows = [r for r in rows if len(r) >= 2]
    if len(rows) < 2:
        return None
    cats = categories or sorted({v for vals in rows for v in vals})
    cidx = {c: i for i, c in enumerate(cats)}
    k = len(cats)
    if k < 2:
        return None
    dist = _ordinal_distance(cats)
    hist = [[0] * k for _ in rows]
    for i, vals in enumerate(rows):
        for v in vals:
            hist[i][cidx[v]] += 1
    n_by_item = [sum(r) for r in hist]
    N = sum(n_by_item)
    if N == 0:
        return None
    p_o = 0.0
    for i in range(len(rows)):
        n = n_by_item[i]
        if n < 2:
            continue
        for a in range(k):
            for b in range(k):
                p_o += hist[i][a] * hist[i][b] * dist[(a, b)] / (n - 1)
    p_o /= N
    p_j = [sum(hist[i][j] for i in range(len(rows))) / N for j in range(k)]
    p_e = sum(p_j[a] * p_j[b] * dist[(a, b)] for a in range(k) for b in range(k))
    if p_e <= 0:
        return None
    return max(-1.0, min(1.0, 1.0 - (p_o / p_e)))


# ---------------------------------------------------------------- consensus


def consensus_label(table: dict, tie_break=None) -> dict:
    """Dawid-Skene style consensus: estimate each item's latent grade by
    iteratively reweighting each judge's vote by their agreement with the other
    judges.

    This is the substitute for a perfect oracle. A judge that votes 5 on
    everything drifts away from consensus and is downweighted; a judge that
    tracks the panel dominates. No ground truth is used or required, so this
    works in exactly the situation the project is in.

    Weighting detail that matters: a judge is scored on agreement with the OTHER
    judges, never with the item's own current estimate. The earlier version
    tested `estimate in other_votes`, which lets a judge agree with itself via a
    tie and gave every judge weight 1.0 on random data - the weight carried no
    information, so the "consensus" was just plurality voting with extra steps.
    Pairwise agreement with the other raters is what actually distinguishes a
    reliable rater from a noisy one.
    """
    items = [
        i
        for i, row in table.items()
        if sum(1 for v in row.values() if v is not None) >= 2
    ]
    if not items:
        return {
            "per_item": {},
            "judge_weights": {},
            "items": 0,
            "judges": [],
            "weight_spread": 0.0,
            "note": "no item carries at least two usable ratings, so consensus is "
            "undefined. A panel of one judge, or a panel where every judge "
            "failed on the same items, yields no consensus.",
        }
    judges = sorted({j for row in table.values() for j in row if row[j] is not None})
    weights = {j: 1.0 for j in judges}
    est = {}
    for _ in range(32):
        for item in items:
            tally = defaultdict(float)
            for j, v in table[item].items():
                if v is not None:
                    tally[v] += weights[j]
            if not tally:
                continue
            est[item] = max(sorted(tally), key=lambda v: (tally[v], -v))
        for j in judges:
            agree = total = 0
            for item in items:
                others = [v for k, v in table[item].items() if k != j and v is not None]
                mine = table[item].get(j)
                if mine is None or not others:
                    continue
                total += 1
                # graded agreement against other raters, so a judge that is off
                # by one is partially right rather than fully wrong
                agree += sum(1.0 - min(1.0, abs(mine - o) / 4.0) for o in others) / len(
                    others
                )
            weights[j] = 0.2 + 0.8 * (agree / total) if total else 1.0
    out = {}
    for item in items:
        votes = [v for v in table[item].values() if v is not None]
        dist = Counter(votes)
        est_g = est.get(item)
        if tie_break:
            est_g = tie_break(est_g, dist)
        ordered = sorted(dist.values(), reverse=True)
        top = ordered[0] if ordered else 0
        second = ordered[1] if len(ordered) > 1 else 0
        out[item] = {
            "consensus_grade": est_g,
            "votes": dict(sorted(dist.items())),
            "n_judges": len(votes),
            "agreement": round(top / len(votes), 4) if votes else None,
            "margin": round((top - second) / len(votes), 4)
            if len(ordered) > 1
            else None,
            "split": len(dist) > 1,
        }
    return {
        "per_item": out,
        "judge_weights": {j: round(w, 4) for j, w in weights.items()},
        "items": len(items),
        "judges": judges,
        "weight_spread": round(max(weights.values()) - min(weights.values()), 4),
    }


# ---------------------------------------------------------------- metrics


def compare_to_reference(
    judgments: list, reference: dict, basis: str = BASIS_TIER
) -> dict:
    """Score one judge (or a panel consensus) against a reference label.

    reference: item_id -> grade in 1..5. Coverage is reported beside every
    metric, because a 0.90 accuracy computed over 15% of items is not a 0.90.
    """
    pairs = []
    for r in judgments:
        if r.get("status") != "graded" or r.get("grade") is None:
            continue
        ref = reference.get(r["item_id"])
        if ref is None:
            continue
        pairs.append((ref, r["grade"], bool(r.get("critical_failure"))))
    n = len(pairs)
    if n == 0:
        return {
            "basis": basis,
            "n": 0,
            "coverage": 0.0,
            "exact_tier_match": None,
            "mae_vs_reference": None,
            "within_1": None,
            "spearman": None,
            "critical": None,
            "coverage_note": "no overlapping items with the reference label; "
            "metrics are None rather than 0.0 so an empty "
            "comparison cannot be mistaken for total failure",
        }
    exact = sum(a == b for a, b, _ in pairs) / n
    mae = statistics.mean(abs(a - b) for a, b, _ in pairs)
    # ordinal correlation against a 1-5 scale
    rho = _spearman([a for a, _, _ in pairs], [b for _, b, _ in pairs])
    within1 = sum(abs(a - b) <= 1 for a, b, _ in pairs) / n
    # critical detection: reference says critical (<=2) and judge agrees
    ref_crit = [(a <= 2, c) for a, _, c in pairs]
    tp = sum(1 for rc, jc in ref_crit if rc and jc)
    fp = sum(1 for rc, jc in ref_crit if not rc and jc)
    fn = sum(1 for rc, jc in ref_crit if rc and not jc)
    tn = sum(1 for rc, jc in ref_crit if not rc and not jc)
    crit = {
        "reference_critical_rate": round((tp + fn) / n, 4),
        "judge_critical_rate": round((tp + fp) / n, 4),
        "critical_recall": round(tp / (tp + fn), 4) if (tp + fn) else None,
        "critical_precision": round(tp / (tp + fp), 4) if (tp + fp) else None,
        "critical_accuracy": round((tp + tn) / n, 4),
        "critical_f1": round(2 * tp / (2 * tp + fp + fn), 4)
        if (2 * tp + fp + fn)
        else None,
    }
    return {
        "basis": basis,
        "n": n,
        "exact_tier_match": round(exact, 4),
        "mae_vs_reference": round(mae, 4),
        "within_1": round(within1, 4),
        "spearman": rho,
        "critical": crit,
        "coverage_note": "n is the number of items scored against the reference; "
        "items with no reference label are excluded, not defaulted.",
    }


def _spearman(a: list, b: list) -> float | None:
    if len(a) < 3 or any(x is None for x in a + b):
        return None

    def rank(x):
        order = sorted(range(len(x)), key=lambda i: x[i])
        out = [0.0] * len(x)
        i = 0
        while i < len(order):
            j = i
            while j + 1 < len(order) and x[order[j + 1]] == x[order[i]]:
                j += 1
            avg = (i + j) / 2.0 + 1.0
            for k in range(i, j + 1):
                out[order[k]] = avg
            i = j + 1
        return out

    ra, rb = rank(a), rank(b)
    n = len(a)
    ma, mb = statistics.mean(ra), statistics.mean(rb)
    num = sum((x - ma) * (y - mb) for x, y in zip(ra, rb))
    den = (sum((x - ma) ** 2 for x in ra) * sum((y - mb) ** 2 for y in rb)) ** 0.5
    return round(num / den, 4) if den else None


def wilson_interval(successes: int, n: int, z: float = 1.96) -> dict:
    """Wilson score interval.

    Preferred over the normal approximation here because several of these rates
    sit near 0 or 1 on small n, where the normal interval runs below 0 or above
    1 and is simply wrong.
    """
    if n <= 0:
        return {"low": None, "high": None, "n": 0}
    p = successes / n
    d = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    half = (z / d) * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return {
        "low": round(max(0.0, centre - half), 4),
        "high": round(min(1.0, centre + half), 4),
        "point": round(p, 4),
        "n": n,
    }


# ---------------------------------------------------------------- report


def rater_coverage(table: dict) -> dict:
    """How many raters each item actually received, and how often 2-rater items
    were unanimous.

    This is the gate on interpreting any agreement number. Fleiss' kappa in
    particular saturates when many items have only two raters that agree: with
    2 raters P_i is either 0 or 1, so a handful of unanimous pairs drags the
    statistic to 1.0 regardless of how the 3-rater items look. Measured on the
    first real panel, 13/30 items had 2 raters and 12 of those were unanimous,
    which put Fleiss at exactly 1.00 beside an alpha of 0.63.
    """
    sizes = Counter()
    unanimous_two = 0
    two = 0
    for row in table.values():
        vals = [v for v in row.values() if v is not None]
        sizes[len(vals)] += 1
        if len(vals) == 2:
            two += 1
            if vals[0] == vals[1]:
                unanimous_two += 1
    n = len(table) or 1
    full = sizes.get(max(sizes) if sizes else 0, 0)
    return {
        "items": len(table),
        "raters_per_item": dict(sorted(sizes.items())),
        "items_with_two_raters": two,
        "two_rater_items_unanimous": unanimous_two,
        "two_rater_unanimous_share": round(unanimous_two / n, 4),
        "max_raters_observed": max(sizes) if sizes else 0,
        "warning": (
            "Most units have only two observed raters. Report missingness "
            "and per-arm agreement alongside the pooled statistic."
        )
        if two / n > 0.3
        else None,
    }


def panel_report(
    records: list, reference: dict = None, basis: str = BASIS_TIER
) -> dict:
    """The benchmark-level view: who judged, how well they agree with each other,
    and how each scores against the reference basis."""
    judges = sorted({r.get("judge") for r in records if r.get("judge")})
    table = ordinal_matrix(records)
    by_judge = {j: [r for r in records if r.get("judge") == j] for j in judges}
    per_judge = {}
    for j in judges:
        rows = by_judge[j]
        graded = [r for r in rows if r.get("status") == "graded"]
        per_judge[j] = {
            "judge_provider": next(
                (r.get("judge_provider") for r in rows if r.get("judge_provider")), None
            ),
            "attempted": len(rows),
            "graded": len(graded),
            "valid_rate": round(len(graded) / len(rows), 4) if rows else None,
            "statuses": dict(Counter(r.get("status") for r in rows)),
            "abstain_rate": round(
                sum(1 for r in graded if r.get("abstain")) / len(graded), 4
            )
            if graded
            else None,
            "critical_rate": round(
                sum(1 for r in graded if r.get("critical_failure")) / len(graded), 4
            )
            if graded
            else None,
            "grade_mean": round(statistics.mean(r["grade"] for r in graded), 4)
            if graded
            else None,
            "grade_dist": dict(sorted(Counter(r["grade"] for r in graded).items()))
            if graded
            else None,
            "sd_across_repeats": _mean_sd(rows),
        }
        if reference:
            per_judge[j]["vs_reference"] = compare_to_reference(rows, reference, basis)

    cons = consensus_label(table)
    return {
        "panel_protocol": PANEL_PROTOCOL,
        "rater_coverage": rater_coverage(table),
        "judges": judges,
        "judge_count": len(judges),
        "items": len(table),
        "label_basis": basis,
        "per_judge": per_judge,
        "agreement": {
            "krippendorff_alpha_ordinal": krippendorff_alpha(table),
            "fleiss_kappa": fleiss_kappa(table),
            "quadratic_weighted_kappa": weighted_kappa(table),
            "note": "Computed from mutual agreement only, so these describe judge "
            "reliability without requiring any ground-truth label. A panel of "
            "one yields None: agreement is undefined, not perfect.",
        },
        "consensus": cons,
        "interpretation": [
            "A judge panel with agreement statistics is the minimum apparatus for "
            "comparing systems; a single judge cannot support a ranking claim.",
            "These metrics measure the judges, not the systems under test. A judge "
            "panel with kappa near zero cannot rank anything, however good the "
            "candidate models are.",
        ],
    }


def _mean_sd(rows: list) -> float | None:
    sds = [r["grade_sd"] for r in rows if r.get("grade_sd") is not None]
    return round(statistics.mean(sds), 4) if sds else None
