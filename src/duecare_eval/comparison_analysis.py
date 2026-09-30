"""Offline comparisons on captured typed decisions and separately assessed tiers.

The sampling units are the declared scenario groups. Matched comparisons use
identical task IDs, and coverage always uses the full requested task population.
"""
from collections import Counter, defaultdict
from hashlib import sha256
from itertools import combinations
import json
import math
from pathlib import Path
import random
from statistics import mean

TASK_FIELDS = {"suite", "task_id", "task_sha256", "decision_type", "expected",
               "choices", "labels", "family", "group_id", "split", "facets"}
OBS_FIELDS = {"suite", "model_id", "task_id", "status", "decision", "attempt",
              "request_sha256", "receipt_sha256", "model_reported"}
TYPES = {"binary_probability", "ordinal_distribution", "categorical_distribution",
         "multilabel_probabilities"}
STATUSES = {"completed", "invalid_decision", "provider_error", "invalid", "ungradeable",
            "quota", "budget_or_quota_stop", "credential_unavailable", "timeout",
            "failed", "unknown_outcome", "error", "schema_error", "invalid_response", "truncated"}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False)


def rows(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]


def probability(value):
    return type(value) in (int, float) and math.isfinite(value) and 0 <= value <= 1


def digest(value):
    return isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def normalized(task, decision):
    """Validate exact projected schema, preserving raw mass before normalization.

    Categorical and ordinal receipts retain their original numeric components.
    Scoring normalizes their positive mass, following the executed score contract.
    """
    if not isinstance(decision, dict):
        raise ValueError("invalid_decision_object")
    kind = task["decision_type"]
    if kind == "binary_probability":
        if set(decision) != {"probability"} or not probability(decision["probability"]):
            raise ValueError("invalid_binary_decision")
        return decision, None
    labels = ([str(i) for i in range(1, 6)] if kind == "ordinal_distribution"
              else task["choices"] if kind == "categorical_distribution" else task["labels"])
    probs = decision.get("probabilities")
    if (set(decision) != {"probabilities"} or not isinstance(probs, dict)
            or set(probs) != set(labels) or not all(probability(v) for v in probs.values())):
        raise ValueError("invalid_distribution_keys_or_values")
    mass = sum(probs.values())
    if kind == "multilabel_probabilities":
        return decision, None
    if mass <= 0:
        raise ValueError("empty_distribution")
    return {"probabilities": {k: probs[k] / mass for k in labels}}, mass


def validate(tasks, observations, models):
    lookup = {}
    for task in tasks:
        key = (task.get("suite"), task.get("task_id"))
        if set(task) != TASK_FIELDS or key in lookup or not all(isinstance(x, str) and x for x in key):
            raise ValueError("invalid_or_duplicate_task")
        if task["decision_type"] not in TYPES or not digest(task["task_sha256"]):
            raise ValueError("invalid_task_type_or_digest")
        expected, kind = task["expected"], task["decision_type"]
        if kind == "binary_probability" and type(expected) is not bool:
            raise ValueError("invalid_binary_reference")
        if kind == "ordinal_distribution" and (type(expected) is not int or expected not in range(1, 6)):
            raise ValueError("invalid_ordinal_reference")
        for field in ("choices", "labels"):
            labels = task[field]
            if not isinstance(labels, list) or any(not isinstance(k, str) for k in labels) or len(labels) != len(set(labels)):
                raise ValueError("invalid_reference_labels")
        if kind == "categorical_distribution" and (len(task["choices"]) < 2 or expected not in task["choices"]):
            raise ValueError("invalid_category_reference")
        if kind == "multilabel_probabilities" and (not task["labels"] or not isinstance(expected, list) or not set(expected) <= set(task["labels"])):
            raise ValueError("invalid_multilabel_reference")
        if not isinstance(task["facets"], dict) or any(not isinstance(k, str) or not isinstance(v, (str, bool, int)) for k, v in task["facets"].items()):
            raise ValueError("invalid_facets")
        if not isinstance(task["family"], str) or not isinstance(task["group_id"], str) or not task["group_id"]:
            raise ValueError("invalid_group_or_family")
        lookup[key] = task
    seen = set()
    for row in observations:
        key = (row.get("suite"), row.get("model_id"), row.get("task_id"))
        if set(row) != OBS_FIELDS or key in seen or (key[0], key[2]) not in lookup or key[1] not in models:
            raise ValueError("unknown_or_duplicate_observation")
        if row["status"] not in STATUSES or type(row["attempt"]) is not int or row["attempt"] < 1:
            raise ValueError("invalid_observation_status_or_attempt")
        if not digest(row["receipt_sha256"]) or (row["request_sha256"] is not None and not digest(row["request_sha256"])):
            raise ValueError("invalid_observation_digest")
        if row["status"] == "completed":
            normalized(lookup[(key[0], key[2])], row["decision"])
        elif row["decision"] is not None:
            raise ValueError("unsuccessful_observation_has_decision")
        seen.add(key)
    return lookup


def score(task, decision):
    value, mass = normalized(task, decision)
    kind, expected = task["decision_type"], task["expected"]
    out = {"task_id": task["task_id"], "group_id": task["group_id"], "family": task["family"],
           "decision_type": kind, "facets": task["facets"], "raw_probability_mass": mass}
    if kind == "binary_probability":
        p = value["probability"]
        out.update(correct=(p >= .5) == expected, brier=(p - int(expected)) ** 2,
                   probability=p, expected=expected)
    else:
        probs = value["probabilities"]
        labels = list(probs)
        if kind == "multilabel_probabilities":
            predicted = {k for k, v in probs.items() if v >= .5}
            out.update(correct=predicted == set(expected),
                       brier=mean((probs[k] - int(k in expected)) ** 2 for k in labels))
        else:
            winner = max(labels, key=lambda k: probs[k])
            out["ambiguous_maximum"] = sum(v == max(probs.values()) for v in probs.values()) > 1
            out["correct"] = winner == str(expected)
            if kind == "ordinal_distribution":
                out["expected_grade_mae"] = abs(sum(int(k) * v for k, v in probs.items()) - expected)
                out["ranked_probability_score"] = mean((sum(probs[str(j)] for j in range(1, k + 1)) - int(expected <= k)) ** 2 for k in range(1, 5))
            else:
                out["brier"] = mean((probs[k] - int(k == expected)) ** 2 for k in labels)
    return out


def metrics(scored, requested=None):
    requested = len(scored) if requested is None else requested
    correct = sum(r["correct"] for r in scored)
    result = {"requested": requested, "usable": len(scored), "correct": correct,
              "coverage": len(scored) / requested if requested else None,
              "accuracy_on_usable": correct / len(scored) if scored else None,
              "correct_over_requested": correct / requested if requested else None,
              "scenario_groups": len({r["group_id"] for r in scored})}
    for name in ("brier", "expected_grade_mae", "ranked_probability_score"):
        values = [r[name] for r in scored if name in r]
        result[name] = mean(values) if values else None
    result["ambiguous_maxima"] = sum(r.get("ambiguous_maximum", False) for r in scored)
    result["renormalized_distributions"] = sum(r["raw_probability_mass"] is not None and abs(r["raw_probability_mass"] - 1) > 1e-9 for r in scored)
    return result


def grouped(scored, tasks):
    facets = sorted({k for t in tasks for k in t["facets"]} | {"family", "decision_type"})
    result = {}
    for facet in facets:
        def value(row):
            return row[facet] if facet in {"family", "decision_type"} else row["facets"].get(facet)
        denominators = Counter(str(value(t)) for t in tasks if value(t) is not None)
        buckets = defaultdict(list)
        for row in scored:
            if value(row) is not None:
                buckets[str(value(row))].append(row)
        result[facet] = {v: metrics(buckets[v], n) for v, n in sorted(denominators.items())}
    return result


def paired_uncertainty(left, right, seed=20260930, replicates=500):
    common = sorted(set(left) & set(right))
    groups = defaultdict(list)
    for key in common:
        if left[key]["group_id"] != right[key]["group_id"]:
            raise ValueError("paired_group_mismatch")
        groups[left[key]["group_id"]].append(int(left[key]["correct"]) - int(right[key]["correct"]))
    cells = [(sum(values), len(values)) for _, values in sorted(groups.items())]
    result = {"matched_tasks": len(common), "scenario_groups": len(cells),
              "accuracy_difference_left_minus_right": mean([int(left[k]["correct"]) - int(right[k]["correct"]) for k in common]) if common else None,
              "cluster_bootstrap_95_interval": None, "bootstrap_replicates": 0,
              "resampling_unit": "declared scenario group; task-weighted difference"}
    if len(cells) >= 10:
        rng = random.Random(seed)
        sampled = []
        for _ in range(replicates):
            draw = rng.choices(cells, k=len(cells))
            sampled.append(sum(s for s, _ in draw) / sum(n for _, n in draw))
        sampled.sort()
        result.update(cluster_bootstrap_95_interval=[sampled[int(.025 * (replicates - 1))], sampled[int(.975 * (replicates - 1))]], bootstrap_replicates=replicates)
    return result


def decision_summary(tasks, observations, models):
    validate(tasks, observations, models)
    suites = {}
    for suite in sorted({t["suite"] for t in tasks}):
        population = [t for t in tasks if t["suite"] == suite]
        lookup = {t["task_id"]: t for t in population}
        scored, per_model = {}, {}
        for model in models:
            receipts = [r for r in observations if r["suite"] == suite and r["model_id"] == model]
            scored[model] = {r["task_id"]: score(lookup[r["task_id"]], r["decision"]) for r in receipts if r["status"] == "completed"}
            values = list(scored[model].values())
            per_model[model] = {**metrics(values, len(population)),
                "missing": len(population) - len(receipts), "outcomes": dict(sorted(Counter(r["status"] for r in receipts).items())),
                "reported_model_ids": dict(sorted(Counter(r["model_reported"] for r in receipts if r["model_reported"] is not None).items())),
                "by_facet": grouped(values, population)}
        common = set.intersection(*(set(scored[m]) for m in models))
        matched_tasks = [t for t in population if t["task_id"] in common]
        matched = {m: {**metrics([scored[m][k] for k in sorted(common)]),
                       "by_facet": grouped([scored[m][k] for k in sorted(common)], matched_tasks)} for m in models}
        pairwise = []
        for left, right in combinations(models, 2):
            ids = sorted(set(scored[left]) & set(scored[right]))
            pairwise.append({"left": left, "right": right,
                **paired_uncertainty(scored[left], scored[right]),
                "left_metrics": metrics([scored[left][k] for k in ids]),
                "right_metrics": metrics([scored[right][k] for k in ids])})
        suites[suite] = {"requested_per_model": len(population), "models": per_model,
                         "all_model_intersection": {"tasks": len(common), "models": matched}, "pairwise": pairwise}
    return suites


def tier_summary(requests, observations):
    required = {"campaign", "producer", "request_id", "case_id", "requested_tier", "requested_band", "style"}
    obs_fields = {"campaign", "producer", "judge", "request_id", "status", "grade", "abstain", "critical_failure", "receipt_sha256"}
    lookup = {}
    for row in requests:
        key = (row.get("campaign"), row.get("producer"), row.get("request_id"))
        if set(row) != required or key in lookup or (row["requested_tier"] is not None and (type(row["requested_tier"]) is not int or row["requested_tier"] not in range(1, 6))):
            raise ValueError("invalid_tier_request")
        lookup[key] = row
    seen, groups = set(), defaultdict(list)
    for row in observations:
        key = (row.get("campaign"), row.get("producer"), row.get("request_id"))
        full = (*key, row.get("judge"))
        if set(row) != obs_fields or key not in lookup or full in seen or not digest(row["receipt_sha256"]):
            raise ValueError("invalid_tier_observation")
        if row["status"] not in STATUSES or type(row["abstain"]) is not bool or type(row["critical_failure"]) is not bool:
            raise ValueError("invalid_tier_status")
        if row["grade"] is not None and (type(row["grade"]) is not int or row["grade"] not in range(1, 6)):
            raise ValueError("invalid_measured_grade")
        seen.add(full)
        groups[(row["campaign"], row["producer"], row["judge"])].append((lookup[key], row))
    result = []
    for (campaign, producer, judge), pairs in sorted(groups.items()):
        population = [r for r in requests if r["campaign"] == campaign and r["producer"] == producer]
        usable = [(r, o) for r, o in pairs if o["status"] == "completed" and o["grade"] is not None and not o["abstain"]]
        def summarize(subset, requested):
            defined = [(r, o) for r, o in subset if r["requested_tier"] is not None]
            return {"requested": requested, "assessed": len(subset),
                "coverage": len(subset) / requested if requested else None,
                "mean_assessed_grade": mean(o["grade"] for _, o in subset) if subset else None,
                "critical_failures": sum(o["critical_failure"] for _, o in subset),
                "tier_comparisons": len(defined), "exact_tier_matches": sum(r["requested_tier"] == o["grade"] for r, o in defined),
                "mean_absolute_tier_difference": mean(abs(r["requested_tier"] - o["grade"]) for r, o in defined) if defined else None,
                "requested_assessed_matrix": {str(t): {str(g): sum(r["requested_tier"] == t and o["grade"] == g for r, o in defined) for g in range(1, 6)} for t in range(1, 6)}}
        item = {"campaign": campaign, "producer": producer, "judge": judge, **summarize(usable, len(population)),
                "outcomes": dict(sorted(Counter(o["status"] for _, o in pairs).items())), "missing": len(population) - len(pairs),
                "abstentions": sum(o["abstain"] for _, o in pairs)}
        item["by_requested_tier"] = {str(t): summarize([(r, o) for r, o in usable if r["requested_tier"] == t], sum(r["requested_tier"] == t for r in population)) for t in range(1, 6) if any(r["requested_tier"] == t for r in population)}
        result.append(item)
    return result


def reproduce(root):
    root = Path(root)
    manifest = json.loads((root / "snapshot.json").read_text())
    if manifest.get("schema") != "duecare-comparison-snapshot/1.0.0":
        raise ValueError("unknown_snapshot_schema")
    for name, receipt in manifest["files"].items():
        path = root / name
        if Path(name).name != name or sha256(path.read_bytes()).hexdigest() != receipt["sha256"]:
            raise ValueError("snapshot_file_digest_mismatch")
    return {"schema": "duecare-comparison-findings/1.0.0", "snapshot_at": manifest["snapshot_at"],
        "models": manifest["models"], "suites": decision_summary(rows(root / "tasks.jsonl"), rows(root / "observations.jsonl"), list(manifest["models"])),
        "tier_assessment": tier_summary(rows(root / "tier_requests.jsonl"), rows(root / "tier_observations.jsonl")),
        "operational_coverage": json.loads((root / "coverage.json").read_text()),
        "interpretation": {"population": "Captured benchmark tasks with declared structural and screening-policy references.",
            "comparison": "All-model and pairwise comparisons each use their exact shared usable task IDs; collection follows each campaign's recorded order.",
            "uncertainty": "Deterministic 500-replicate group bootstrap describes resampling variation within captured scenario groups; related templates constrain generalization.",
            "grades": "Requested tiers are generation instructions; measured grades are separate judge assessments.",
            "validation": "Independent worker, legal, language and domain review remains open."}}
