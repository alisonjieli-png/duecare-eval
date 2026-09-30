"""Offline scoring for the declared references in the worked rubric examples."""
from collections import Counter
from decimal import Decimal, InvalidOperation
import math


REFERENCE_TYPES = {
    "indicator_set": {"declared_case_facts"},
    "binary_probability": {"declared_case_facts", "declared_evidence_scope", "declared_action_policy"},
    "numeric": {"arithmetic_identity"},
    "categorical": {"declared_action_policy", "declared_response_policy", "controlled_equivalence_reference"},
    "ranking": {"declared_action_policy"},
}


def decimal_value(value):
    if isinstance(value, bool) or not isinstance(value, (str, int, float, Decimal)):
        raise ValueError("A numeric answer must be a finite number or decimal string.")
    try:
        result = Decimal(str(value))
    except InvalidOperation as error:
        raise ValueError("A numeric answer must be a finite number or decimal string.") from error
    if not result.is_finite():
        raise ValueError("A numeric answer must be finite.")
    return result


def calculation_value(calculation):
    values = [decimal_value(value) for value in calculation["operands"]]
    if len(values) != 2:
        raise ValueError("Worked arithmetic calculations require two operands.")
    if calculation["operation"] == "add":
        return values[0] + values[1]
    if calculation["operation"] == "subtract":
        return values[0] - values[1]
    if calculation["operation"] == "multiply":
        return values[0] * values[1]
    raise ValueError("Use a declared add, subtract or multiply calculation.")


def unique_strings(values):
    return isinstance(values, list) and all(isinstance(v, str) for v in values) and len(set(values)) == len(values)


def validate_bank(bank):
    if bank.get("schema") != "duecare-grading-rubrics/1.0.0":
        raise ValueError("Select a supported rubric bank version.")
    rubrics = {row["id"] for row in bank["rubrics"]}
    if len(rubrics) != len(bank["rubrics"]):
        raise ValueError("Rubric IDs must be unique.")
    ids = set()
    for row in bank["worked_instances"]:
        if row["instance_id"] in ids or row["rubric_id"] not in rubrics:
            raise ValueError("Worked instances need unique IDs and a known rubric.")
        ids.add(row["instance_id"])
        if row.get("reference_basis") not in REFERENCE_TYPES.get(row.get("kind"), set()):
            raise ValueError("Scoring requires an explicit supported reference basis.")
        kind, expected = row["kind"], row["expected"]
        if kind == "indicator_set":
            if not unique_strings(row["labels"]) or not unique_strings(expected) or not set(expected) <= set(row["labels"]):
                raise ValueError("Indicator references must use unique labels from the declared vocabulary.")
        elif kind == "binary_probability":
            if type(expected) is not bool:
                raise ValueError("Binary references must be true or false.")
        elif kind == "numeric":
            if decimal_value(expected) != calculation_value(row["calculation"]):
                raise ValueError("The arithmetic reference differs from its declared calculation.")
            if decimal_value(row["absolute_tolerance"]) < 0:
                raise ValueError("Numeric tolerance must be nonnegative.")
        elif kind in {"categorical", "ranking"}:
            if not unique_strings(row["choices"]):
                raise ValueError("Choices must be unique strings.")
            if kind == "categorical" and expected not in row["choices"]:
                raise ValueError("The reference must be one of the declared choices.")
            if kind == "ranking" and (not unique_strings(expected) or set(expected) != set(row["choices"])):
                raise ValueError("A ranking reference must order every choice exactly once.")
    for example in bank["five_tier_examples"]:
        tiers = [row["tier"] for row in example["responses"]]
        if tiers != [1, 2, 3, 4, 5] or any(not row["text"].strip() for row in example["responses"]):
            raise ValueError("Each teaching array needs all five tiers and a response at every tier.")
        if example["reference_basis"] != "analyst_authored_tier_illustration" or example["model_execution"] != "none":
            raise ValueError("Teaching examples must identify their authorship and execution status.")
    return {"rubrics": len(rubrics), "worked_instances": len(ids),
            "five_tier_cases": len(bank["five_tier_examples"]),
            "illustrative_responses": sum(len(row["responses"]) for row in bank["five_tier_examples"]),
            "kinds": dict(Counter(row["kind"] for row in bank["worked_instances"]))}


def set_metrics(expected, predicted):
    expected, predicted = set(expected), set(predicted)
    tp, fp, fn = len(expected & predicted), len(predicted - expected), len(expected - predicted)
    precision = tp / (tp + fp) if tp + fp else float(not expected)
    recall = tp / (tp + fn) if tp + fn else 1.0
    return {"tp": tp, "fp": fp, "fn": fn, "precision": precision, "recall": recall,
            "f1": 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 1.0,
            "exact_set": expected == predicted}


def score_one(row, answer):
    kind, expected = row["kind"], row["expected"]
    if kind == "indicator_set":
        if not unique_strings(answer) or not set(answer) <= set(row["labels"]):
            raise ValueError("Return unique labels from the declared vocabulary.")
        return {"correct": set(answer) == set(expected), **set_metrics(expected, answer)}
    if kind == "binary_probability":
        if type(answer) not in (int, float) or not math.isfinite(answer) or not 0 <= answer <= 1:
            raise ValueError("Return a finite probability between 0 and 1.")
        bounded = min(max(answer, 1e-15), 1 - 1e-15)
        return {"correct": (answer >= 0.5) == expected, "brier": (answer - int(expected)) ** 2,
                "log_loss": -math.log(bounded if expected else 1 - bounded), "threshold": 0.5}
    if kind == "numeric":
        error = abs(decimal_value(answer) - decimal_value(expected))
        return {"correct": error <= decimal_value(row["absolute_tolerance"]), "absolute_error": str(error)}
    if kind == "categorical":
        if not isinstance(answer, str) or answer not in row["choices"]:
            raise ValueError("Return one declared choice.")
        result = {"correct": answer == expected}
        if "pair_id" in row:
            result["semantic_choice"] = row["display_order"].get(answer, answer)
        return result
    if kind == "ranking":
        if not unique_strings(answer) or set(answer) != set(row["choices"]):
            raise ValueError("Return every declared choice exactly once.")
        position = {value: index for index, value in enumerate(answer)}
        pairs = [(left, right) for i, left in enumerate(expected) for right in expected[i + 1:]]
        concordant = sum(position[left] < position[right] for left, right in pairs)
        return {"correct": answer == expected, "pairwise_order_correct": concordant,
                "pairwise_order_total": len(pairs), "pairwise_order_accuracy": concordant / len(pairs) if pairs else 1.0}
    raise ValueError("Select a supported worked-instance type.")


def score_instances(bank, responses):
    validate_bank(bank)
    tasks = {row["instance_id"]: row for row in bank["worked_instances"]}
    ids = [row["instance_id"] for row in responses]
    if len(set(ids)) != len(ids) or not set(ids) <= set(tasks):
        raise ValueError("Response IDs must be unique and belong to the selected bank.")
    by_id = {row["instance_id"]: row for row in responses}
    outcomes = []
    for instance_id, task in tasks.items():
        output = {"instance_id": instance_id, "kind": task["kind"], "reference_basis": task["reference_basis"]}
        response = by_id.get(instance_id)
        if response is None:
            output["status"] = "missing"
        elif response.get("status") != "completed":
            output["status"] = "unavailable"
            output["response_status"] = response.get("status")
        else:
            try:
                output.update(score_one(task, response.get("answer")), status="assessed")
            except (ValueError, TypeError, KeyError) as error:
                output.update(status="invalid", reason=str(error))
        outcomes.append(output)
    assessed = [row for row in outcomes if row["status"] == "assessed"]
    correct = sum(row["correct"] for row in assessed)
    pair_groups = {}
    for row in assessed:
        task = tasks[row["instance_id"]]
        if "pair_id" in task:
            pair_groups.setdefault(task["pair_id"], []).append(row["semantic_choice"])
    full_pairs = [values for values in pair_groups.values() if len(values) == 2]
    indicator_rows = [row for row in assessed if row["kind"] == "indicator_set"]
    tp = sum(row["tp"] for row in indicator_rows)
    fp = sum(row["fp"] for row in indicator_rows)
    fn = sum(row["fn"] for row in indicator_rows)
    return {"schema": "duecare-worked-rubric-scores/1.0.0", "reference_scope": "analyst_authored_worked_instances",
            "requested": len(tasks), "assessed": len(assessed), "correct": correct,
            "coverage": len(assessed) / len(tasks) if tasks else 0,
            "accuracy_requested": correct / len(tasks) if tasks else None,
            "accuracy_assessed": correct / len(assessed) if assessed else None,
            "statuses": dict(Counter(row["status"] for row in outcomes)),
            "indicator_components": {"assessed_instances": len(indicator_rows), "tp": tp, "fp": fp, "fn": fn,
                "micro_precision": tp / (tp + fp) if tp + fp else None,
                "micro_recall": tp / (tp + fn) if tp + fn else None,
                "micro_f1": 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else None},
            "both_order_pairs": {"complete": len(full_pairs), "consistent": sum(a == b for a, b in full_pairs)},
            "outcomes": outcomes}
