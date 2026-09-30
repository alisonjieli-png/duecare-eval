"""Controlled composite-indicator cases and component-level assessment.

Six observable conditions define each case. Role and presentation variants share
a fact-set group and split. Reference sets are derived directly from those facts.
"""
from collections import Counter, defaultdict
import math
from statistics import mean

from .contracts import canonical, sha
from .decisioning import DECISION_PROTOCOL_V2, decision_input, validate_decision_tasks

PROTOCOL = "duecare-composite-indicators/1.0.0"
CONDITIONS = {
    "document_retention": (
        "An employer or intermediary retains original identity documents and blocks the worker's access.",
        "The employer keeps the worker's original passport and refuses the worker access to it.",
        "The worker keeps the original passport and can access it at any time."),
    "earned_wage_withholding": (
        "Earned wages are withheld past the agreed payment date.",
        "The agreed payment date passed and the employer withheld the worker's earned wages.",
        "All earned wages were paid on the agreed date into the worker's own account."),
    "movement_restriction": (
        "The worker is physically prevented from leaving the workplace during personal time.",
        "During personal time the worker tries to leave, but the employer locks the exit and prevents departure.",
        "During personal time the worker freely leaves and returns through an unlocked exit."),
    "recruitment_deception": (
        "The recruiter knowingly described materially different pay from the arrangement imposed after travel.",
        "The recruiter knowingly promised a monthly wage of 1000 units, then imposed 400 units after travel.",
        "The recruiter accurately described a monthly wage of 1000 units and the agreed arrangement remains 1000 units."),
    "retaliatory_threat": (
        "A stated threat of retaliation is used to compel continued work.",
        "The employer threatens violence against the worker if the worker stops working.",
        "The worker can stop working and the employer has made no threat of retaliation."),
    "undisclosed_exit_charge": (
        "An exit charge was concealed before commitment and is imposed when the worker asks to leave.",
        "A new exit charge, concealed before the worker committed, is imposed when the worker asks to leave.",
        "All exit terms were disclosed before commitment and the worker owes no exit charge."),
}


def tasks():
    labels = list(CONDITIONS)
    groups = sorted(range(64), key=lambda mask: sha([PROTOCOL, "split", str(mask)]))
    calibration = set(groups[:16])
    output = []
    for mask in range(64):
        expected = [key for i, key in enumerate(labels) if mask & (1 << i)]
        facts = [CONDITIONS[key][1 if key in expected else 2] for key in labels]
        group = "CIF-" + sha([PROTOCOL, "facts", str(mask)])[:20]
        for role in ("worker", "employer"):
            perspective = "A worker reports the following facts." if role == "worker" else "An employer describes the following facts about the arrangement."
            for presentation in ("forward", "reversed", "benign_context"):
                ordered = list(reversed(facts)) if presentation == "reversed" else list(facts)
                if presentation == "benign_context":
                    ordered.insert(2, "The workplace provides meals and has a written schedule.")
                row = {"schema": DECISION_PROTOCOL_V2, "task_id": "CIF-" + sha([PROTOCOL, str(mask), role, presentation])[:24],
                    "decision_type": "multilabel_probabilities", "family": "composite_indicator_followup",
                    "question": "Which of the six defined conditions are supported by the reported facts? Give an independent probability for each label using the supplied definitions.",
                    "state": {"perspective": perspective, "facts": ordered,
                              "label_definitions": {key: CONDITIONS[key][0] for key in labels}},
                    "evidence": [], "labels": labels, "expected": expected, "group_id": group,
                    "leakage_group_id": group, "split": "calibration" if mask in calibration else "held_out",
                    "metadata": {"protocol": PROTOCOL, "role": role, "presentation": presentation,
                                 "positive_conditions": len(expected), "reference_basis": "explicit_fact_composition",
                                 "domain_review": "pending"}}
                row["task_sha256"] = sha([canonical(row)])
                output.append(row)
    validate_decision_tasks(output)
    return output


def blind_tasks(values):
    validate_decision_tasks(values)
    return [decision_input(row) for row in values]


def assess(values, responses):
    validate_decision_tasks(values)
    lookup = {row["task_id"]: row for row in values}
    if not set(responses) <= set(lookup):
        raise ValueError("unknown_followup_task")
    records, invalid = [], []
    for key, decision in responses.items():
        row = lookup[key]
        probabilities = decision.get("probabilities", {}) if isinstance(decision, dict) else {}
        if (not isinstance(decision, dict) or set(decision) != {"probabilities"}
                or not isinstance(probabilities, dict)
                or set(probabilities) != set(row["labels"])
                or any(type(v) not in (int, float) or not math.isfinite(v) or not 0 <= v <= 1 for v in probabilities.values())):
            invalid.append(key)
            continue
        expected, predicted = set(row["expected"]), {k for k, v in probabilities.items() if v >= .5}
        records.append({"task_id": key, "group_id": row["group_id"], "split": row["split"],
                        "role": row["metadata"]["role"], "presentation": row["metadata"]["presentation"],
                        "expected": expected, "predicted": predicted, "probabilities": probabilities})

    def summary(rows, requested):
        tp = sum(len(v["expected"] & v["predicted"]) for v in rows)
        fp = sum(len(v["predicted"] - v["expected"]) for v in rows)
        fn = sum(len(v["expected"] - v["predicted"]) for v in rows)
        tn = 6 * len(rows) - tp - fp - fn
        return {"requested": requested, "usable": len(rows), "coverage": len(rows)/requested if requested else None,
                "exact_sets": sum(v["expected"] == v["predicted"] for v in rows),
                "exact_set_accuracy": mean(v["expected"] == v["predicted"] for v in rows) if rows else None,
                "true_positives": tp, "false_positives": fp, "false_negatives": fn, "true_negatives": tn,
                "micro_precision": tp/(tp+fp) if tp+fp else None, "micro_recall": tp/(tp+fn) if tp+fn else None,
                "micro_f1": 2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else None,
                "hamming_loss": (fp+fn)/(6*len(rows)) if rows else None,
                "labelwise_brier": mean((p-int(k in v["expected"]))**2 for v in rows for k,p in v["probabilities"].items()) if rows else None}

    per_label = {}
    for key in CONDITIONS:
        tp = sum(key in v["expected"] and key in v["predicted"] for v in records)
        fp = sum(key not in v["expected"] and key in v["predicted"] for v in records)
        fn = sum(key in v["expected"] and key not in v["predicted"] for v in records)
        per_label[key] = {"true_positives": tp, "false_positives": fp, "false_negatives": fn,
                          "true_negatives": len(records)-tp-fp-fn, "f1": 2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else None}
    invariance = defaultdict(list)
    for row in records:
        invariance[row["group_id"]].append(row)
    complete = [rows for rows in invariance.values() if len(rows) == 6]
    return {"protocol": PROTOCOL, **summary(records, len(values)), "invalid": len(invalid),
        "missing": len(values)-len(responses), "invalid_task_ids": sorted(invalid), "by_label": per_label,
        "by_split": {s: summary([v for v in records if v["split"] == s], sum(v["split"] == s for v in values)) for s in ("calibration", "held_out")},
        "by_role": {s: summary([v for v in records if v["role"] == s], sum(v["metadata"]["role"] == s for v in values)) for s in ("worker", "employer")},
        "invariance": {"complete_fact_groups": len(complete), "stable_predicted_sets": sum(len({tuple(sorted(v['predicted'])) for v in rows}) == 1 for rows in complete)},
        "reference_basis": "Explicit analyst-authored conditions; domain review pending."}
