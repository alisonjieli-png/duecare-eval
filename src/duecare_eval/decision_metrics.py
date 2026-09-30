"""Metrics for probabilistic, selective, subgroup and paired decision evaluation.

No single number is allowed to stand in for all of these properties. Accuracy
measures discrimination, proper scoring rules measure probability quality,
risk/coverage measures abstention behaviour, subgroup tables expose tails, and
paired relations test whether a system reacts to the fact that actually changed.
"""
from __future__ import annotations

import math
from collections import Counter, defaultdict


def _mean(values):
    values = [v for v in values if v is not None]
    return sum(values) / len(values) if values else None


def _safe_div(num, den):
    return num / den if den else None


def _round(value, digits=6):
    return None if value is None else round(value, digits)


def fixed_ece_binary(rows: list[dict], bins: int = 10):
    if not rows:
        return None
    total, ece = len(rows), 0.0
    for index in range(bins):
        lo, hi = index / bins, (index + 1) / bins
        bucket = [r for r in rows if lo <= r["probability"] <= hi
                  and (index == bins - 1 or r["probability"] < hi)]
        if bucket:
            confidence = _mean([r["probability"] for r in bucket])
            outcome = _mean([1.0 if r["expected"] else 0.0 for r in bucket])
            ece += len(bucket) / total * abs(confidence - outcome)
    return ece


def adaptive_ece_binary(rows: list[dict], bins: int = 10):
    """Equal-mass ECE, reported beside rather than instead of fixed-bin ECE."""
    if not rows:
        return None
    ordered = sorted(rows, key=lambda row: (row["probability"], row["task_id"]))
    bins = min(bins, len(ordered))
    ece = 0.0
    for index in range(bins):
        start = index * len(ordered) // bins
        end = (index + 1) * len(ordered) // bins
        bucket = ordered[start:end]
        if bucket:
            confidence = _mean([r["probability"] for r in bucket])
            outcome = _mean([1.0 if r["expected"] else 0.0 for r in bucket])
            ece += len(bucket) / len(ordered) * abs(confidence - outcome)
    return ece


def _auroc(rows: list[dict]):
    positives = sum(bool(r["expected"]) for r in rows)
    negatives = len(rows) - positives
    if not positives or not negatives:
        return None
    ordered = sorted(rows, key=lambda row: row["probability"])
    rank_sum, index = 0.0, 0
    while index < len(ordered):
        end = index + 1
        while (end < len(ordered) and
               ordered[end]["probability"] == ordered[index]["probability"]):
            end += 1
        average_rank = (index + 1 + end) / 2.0
        rank_sum += average_rank * sum(bool(r["expected"])
                                      for r in ordered[index:end])
        index = end
    return (rank_sum - positives * (positives + 1) / 2) / (positives * negatives)


def _average_precision(rows: list[dict]):
    positives = sum(bool(r["expected"]) for r in rows)
    if not positives:
        return None
    ordered = sorted(rows, key=lambda row: (-row["probability"], row["task_id"]))
    hits, total = 0, 0.0
    for rank, row in enumerate(ordered, 1):
        if row["expected"]:
            hits += 1
            total += hits / rank
    return total / positives


def binary_metrics(rows: list[dict]) -> dict:
    tp = sum(r["verdict"] and r["expected"] for r in rows)
    tn = sum(not r["verdict"] and not r["expected"] for r in rows)
    fp = sum(r["verdict"] and not r["expected"] for r in rows)
    fn = sum(not r["verdict"] and r["expected"] for r in rows)
    precision = _safe_div(tp, tp + fp)
    recall = _safe_div(tp, tp + fn)
    specificity = _safe_div(tn, tn + fp)
    f1 = (2 * precision * recall / (precision + recall)
          if precision is not None and recall is not None and precision + recall else None)
    denominator = math.sqrt((tp + fp) * (tp + fn) * (tn + fp) * (tn + fn))
    mcc = (tp * tn - fp * fn) / denominator if denominator else None
    conditional = {}
    for expected in (False, True):
        subset = [row for row in rows if row["expected"] is expected]
        conditional[str(expected).lower()] = {
            "n": len(subset),
            "accuracy": _round(_mean([1.0 if row["correct"] else 0.0
                                       for row in subset])),
            "brier": _round(_mean([row["brier"] for row in subset])),
            "mean_probability": _round(_mean([row["probability"] for row in subset])),
        }
    return {
        "n": len(rows), "positives": tp + fn, "negatives": tn + fp,
        "accuracy": _round(_safe_div(tp + tn, len(rows))),
        "balanced_accuracy": _round(_mean([recall, specificity])),
        "precision": _round(precision), "recall": _round(recall),
        "specificity": _round(specificity), "f1": _round(f1),
        "matthews_correlation": _round(mcc),
        "confusion": {"tp": tp, "tn": tn, "fp": fp, "fn": fn},
        "brier": _round(_mean([r["brier"] for r in rows])),
        "log_loss": _round(_mean([r["log_loss"] for r in rows])),
        "expected_calibration_error": _round(fixed_ece_binary(rows)),
        "adaptive_calibration_error": _round(adaptive_ece_binary(rows)),
        "auroc": _round(_auroc(rows)),
        "average_precision": _round(_average_precision(rows)),
        "class_conditional": conditional,
    }


def _weighted_kappa(rows: list[dict]):
    if len(rows) < 2:
        return None
    labels = range(1, 6)
    observed = Counter((int(r["expected"]), int(r["grade"])) for r in rows)
    actual = Counter(int(r["expected"]) for r in rows)
    predicted = Counter(int(r["grade"]) for r in rows)
    n = len(rows)
    observed_disagreement = sum(
        ((a - b) / 4.0) ** 2 * count for (a, b), count in observed.items()) / n
    expected_disagreement = sum(
        ((a - b) / 4.0) ** 2 * actual[a] * predicted[b] / (n * n)
        for a in labels for b in labels)
    if expected_disagreement == 0:
        return 1.0 if observed_disagreement == 0 else None
    return 1.0 - observed_disagreement / expected_disagreement


def ordinal_metrics(rows: list[dict]) -> dict:
    return {
        "n": len(rows),
        "accuracy": _round(_mean([1.0 if r["correct"] else 0.0 for r in rows])),
        "mae": _round(_mean([r["absolute_error"] for r in rows])),
        "ranked_probability_score": _round(
            _mean([r["ranked_probability_score"] for r in rows])),
        "quadratic_weighted_kappa": _round(_weighted_kappa(rows)),
    }


def categorical_metrics(rows: list[dict]) -> dict:
    labels = sorted({choice for row in rows for choice in row["choices"]})
    per_label = {}
    for label in labels:
        tp = sum(r["choice"] == label and r["expected"] == label for r in rows)
        fp = sum(r["choice"] == label and r["expected"] != label for r in rows)
        fn = sum(r["choice"] != label and r["expected"] == label for r in rows)
        precision, recall = _safe_div(tp, tp + fp), _safe_div(tp, tp + fn)
        f1 = (2 * precision * recall / (precision + recall)
              if precision is not None and recall is not None and precision + recall else 0.0)
        per_label[label] = {"n": sum(r["expected"] == label for r in rows),
                            "precision": _round(precision), "recall": _round(recall),
                            "f1": _round(f1)}
    return {
        "n": len(rows),
        "accuracy": _round(_mean([1.0 if r["correct"] else 0.0 for r in rows])),
        "top2_accuracy": _round(_mean([1.0 if r["top2_correct"] else 0.0
                                        for r in rows])),
        "macro_f1": _round(_mean([v["f1"] for v in per_label.values()])),
        "brier": _round(_mean([r["brier"] for r in rows])),
        "log_loss": _round(_mean([r["log_loss"] for r in rows])),
        "per_label": per_label,
    }


def multilabel_metrics(rows: list[dict]) -> dict:
    labels = sorted({label for row in rows for label in row["labels"]})
    tp = fp = fn = 0
    per_label = {}
    for label in labels:
        ltp = sum(label in r["predicted_labels"] and label in r["expected"] for r in rows)
        lfp = sum(label in r["predicted_labels"] and label not in r["expected"] for r in rows)
        lfn = sum(label not in r["predicted_labels"] and label in r["expected"] for r in rows)
        tp += ltp; fp += lfp; fn += lfn
        precision, recall = _safe_div(ltp, ltp + lfp), _safe_div(ltp, ltp + lfn)
        f1 = (2 * precision * recall / (precision + recall)
              if precision is not None and recall is not None and precision + recall else 0.0)
        per_label[label] = {"support": sum(label in r["expected"] for r in rows),
                            "precision": _round(precision), "recall": _round(recall),
                            "f1": _round(f1)}
    micro_precision, micro_recall = _safe_div(tp, tp + fp), _safe_div(tp, tp + fn)
    micro_f1 = (2 * micro_precision * micro_recall / (micro_precision + micro_recall)
                if micro_precision is not None and micro_recall is not None
                and micro_precision + micro_recall else None)
    return {
        "n": len(rows),
        "exact_set_accuracy": _round(_mean([1.0 if r["correct"] else 0.0 for r in rows])),
        "hamming_loss": _round(_mean([r["hamming_loss"] for r in rows])),
        "brier": _round(_mean([r["brier"] for r in rows])),
        "micro_precision": _round(micro_precision),
        "micro_recall": _round(micro_recall), "micro_f1": _round(micro_f1),
        "macro_f1": _round(_mean([v["f1"] for v in per_label.values()])),
        "per_label": per_label,
    }


def _confidence(row: dict):
    kind = row["decision_type"]
    if kind == "binary_probability":
        return max(row["probability"], 1.0 - row["probability"])
    if kind in {"ordinal_distribution", "categorical_distribution"}:
        return max(row["probabilities"].values())
    if kind == "multilabel_probabilities":
        return _mean([max(p, 1.0 - p) for p in row["probabilities"].values()])
    return None


def selective_risk(rows: list[dict]) -> dict:
    usable = [(float(_confidence(row)), row) for row in rows
              if _confidence(row) is not None]
    if not usable:
        return {"n": 0, "aurc": None, "curve": []}
    usable.sort(key=lambda pair: (-pair[0], pair[1]["task_id"]))
    errors, risks, curve = 0, [], []
    checkpoints = {max(1, round(len(usable) * p / 10)) for p in range(1, 11)}
    for index, (confidence, row) in enumerate(usable, 1):
        errors += not row["correct"]
        risk = errors / index
        risks.append(risk)
        if index in checkpoints or index == len(usable):
            curve.append({"coverage": round(index / len(usable), 4),
                          "risk": round(risk, 6),
                          "minimum_confidence": round(confidence, 6)})
    return {"n": len(usable), "aurc": _round(_mean(risks)), "curve": curve,
            "note": "Lower AURC is better; inspect class-conditional curves before using abstention."}


def prediction_set_metrics(rows: list[dict], target_coverage: float = 0.9) -> dict:
    """Top-probability prediction sets; diagnostic, not a conformal guarantee."""
    eligible = []
    for row in rows:
        kind = row["decision_type"]
        if kind == "binary_probability":
            probs = {False: 1.0 - row["probability"], True: row["probability"]}
            expected = bool(row["expected"])
        elif kind == "ordinal_distribution":
            probs = {int(key): value for key, value in row["probabilities"].items()}
            expected = int(row["expected"])
        elif kind == "categorical_distribution":
            probs, expected = row["probabilities"], row["expected"]
        else:
            continue
        ordered = sorted(probs, key=lambda label: (-probs[label], str(label)))
        chosen, mass = [], 0.0
        for label in ordered:
            chosen.append(label); mass += probs[label]
            if mass >= target_coverage:
                break
        eligible.append({"contains": expected in chosen, "size": len(chosen)})
    return {
        "n": len(eligible), "target_mass": target_coverage,
        "empirical_coverage": _round(_mean([1.0 if row["contains"] else 0.0
                                             for row in eligible])),
        "average_set_size": _round(_mean([row["size"] for row in eligible])),
        "singleton_rate": _round(_mean([1.0 if row["size"] == 1 else 0.0
                                         for row in eligible])),
        "note": "Diagnostic top-mass sets only; no exchangeability or conformal coverage claim.",
    }


def _predicted_value(row: dict):
    kind = row["decision_type"]
    if kind == "binary_probability":
        return row["verdict"]
    if kind == "ordinal_distribution":
        return row["grade"]
    if kind == "categorical_distribution":
        return row["choice"]
    if kind == "multilabel_probabilities":
        return frozenset(row["predicted_labels"])
    return None


def paired_relation_metrics(tasks: list[dict], rows: list[dict]) -> dict:
    row_by_id = {row["task_id"]: row for row in rows}
    groups = defaultdict(list)
    for task in tasks:
        if task.get("pair_id"):
            groups[task["pair_id"]].append(task)
    results = []
    for pair_id, pair in groups.items():
        if len(pair) != 2 or any(task["task_id"] not in row_by_id for task in pair):
            continue
        pair.sort(key=lambda task: task.get("pair_position", 0))
        first, second = (row_by_id[pair[0]["task_id"]],
                         row_by_id[pair[1]["task_id"]])
        relation = pair[0].get("expected_relation")
        a, b = _predicted_value(first), _predicted_value(second)
        if relation == "flip":
            relation_ok = a != b
        elif relation == "invariant":
            relation_ok = a == b
        elif relation == "monotonic_increase":
            relation_ok = float(a) < float(b)
        elif relation == "set_reduction":
            relation_ok = set(b) < set(a)
        else:
            relation_ok = False
        results.append({"pair_id": pair_id, "relation": relation,
                        "base_correct": first["correct"],
                        "contrast_correct": second["correct"],
                        "both_correct": first["correct"] and second["correct"],
                        "relation_satisfied": relation_ok})
    by_relation = {}
    for relation in sorted({row["relation"] for row in results}):
        subset = [row for row in results if row["relation"] == relation]
        base_correct = [row for row in subset if row["base_correct"]]
        by_relation[relation] = {
            "pairs": len(subset),
            "both_correct_rate": _round(_mean([1.0 if r["both_correct"] else 0.0
                                                for r in subset])),
            "relation_consistency": _round(_mean(
                [1.0 if r["relation_satisfied"] else 0.0 for r in subset])),
            "counterfactual_failure_rate_given_base_correct": _round(
                _mean([0.0 if r["contrast_correct"] else 1.0 for r in base_correct])),
        }
    return {"eligible_pairs": len(results), "by_relation": by_relation,
            "both_correct_rate": _round(_mean([1.0 if r["both_correct"] else 0.0
                                                for r in results])),
            "relation_consistency": _round(_mean(
                [1.0 if r["relation_satisfied"] else 0.0 for r in results]))}


def subgroup_metrics(tasks: list[dict], rows: list[dict], *, min_n: int = 20) -> dict:
    row_by_id = {row["task_id"]: row for row in rows}
    axes = defaultdict(lambda: defaultdict(list))
    for task in tasks:
        task_axes = ((task.get("metadata") or {}).get("axes") or {})
        for axis, value in task_axes.items():
            axes[str(axis)][str(value)].append(task["task_id"])
    report = {}
    for axis, groups in sorted(axes.items()):
        table = []
        for value, task_ids in sorted(groups.items()):
            completed = [row_by_id[task_id] for task_id in task_ids if task_id in row_by_id]
            if len(task_ids) < min_n:
                continue
            table.append({
                "value": value, "tasks": len(task_ids), "completed": len(completed),
                "coverage": _round(_safe_div(len(completed), len(task_ids))),
                "accuracy": _round(_mean([1.0 if r["correct"] else 0.0
                                           for r in completed])),
            })
        eligible = [row for row in table if row["accuracy"] is not None]
        if table:
            report[axis] = {
                "groups": table,
                "worst_accuracy": min(eligible, key=lambda row: row["accuracy"])
                if eligible else None,
                "worst_coverage": min(table, key=lambda row: row["coverage"]),
            }
    return {"minimum_group_size": min_n, "axes": report}


def by_partition(tasks: list[dict], rows: list[dict], field: str) -> dict:
    row_by_id = {row["task_id"]: row for row in rows}
    groups = defaultdict(list)
    for task in tasks:
        value = task.get(field)
        if value is not None:
            groups[str(value)].append(task)
    out = {}
    for value, subset in sorted(groups.items()):
        completed = [row_by_id[t["task_id"]] for t in subset
                     if t["task_id"] in row_by_id]
        out[value] = {
            "tasks": len(subset), "completed": len(completed),
            "coverage": _round(_safe_div(len(completed), len(subset))),
            "accuracy": _round(_mean([1.0 if r["correct"] else 0.0
                                       for r in completed])),
        }
    return out
