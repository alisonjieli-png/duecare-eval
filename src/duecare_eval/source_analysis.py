"""Recompute descriptive findings from released numeric observations, offline.

The matched wording unit is one source text, one view, four questions and two
repeats. Wording span measures question sensitivity; repeat change measures
stability. Accuracy evaluation uses separately established reference answers.
"""
from collections import Counter, defaultdict
import json
import math
from pathlib import Path
from statistics import mean


SOURCE_FIELDS = {"request_id", "case_id", "probe_id", "view_id", "repeat",
                 "track", "model", "decision", "request_sha256"}
STYLE_FIELDS = {"request_id", "model", "winner", "request_sha256"}


def rows(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]


def average(values):
    return mean(values) if values else None


def probability(value):
    return type(value) in (int, float) and math.isfinite(value) and 0 <= value <= 1


def validate_source(observations, catalog):
    seen = set()
    for row in observations:
        if set(row) != SOURCE_FIELDS or row["request_id"] in seen:
            raise ValueError("unexpected_source_fields_or_duplicate_request")
        seen.add(row["request_id"])
        probe = catalog.get(row["probe_id"])
        if probe is None or type(row["repeat"]) is not int or row["repeat"] not in (0, 1):
            raise ValueError("unknown_probe_or_repeat")
        if row["model"] != "jev-1.13.0":
            raise ValueError("mixed_model_protocol")
        decision = row["decision"]
        if probe["decision_type"] == "binary_probability":
            if set(decision) != {"probability"} or not probability(decision["probability"]):
                raise ValueError("invalid_binary_probability")
        else:
            values = decision.get("probabilities", {})
            choices = {str(i) for i in range(1, 6)} if probe["decision_type"] == "ordinal_distribution" else set(probe["choices"])
            if (set(decision) != {"probabilities"} or set(values) != choices
                    or not all(probability(p) for p in values.values())
                    or abs(sum(values.values()) - 1) > .021):
                raise ValueError("invalid_distribution")


def unique_winner(distribution):
    if not distribution:
        return None
    best = max(distribution.values())
    labels = [k for k, v in distribution.items() if v == best]
    return labels[0] if len(labels) == 1 else None


def source_summary(observations, catalog, requested):
    catalog = {p["probe_id"]: p for p in catalog}
    validate_source(observations, catalog)
    if len(observations) > requested:
        raise ValueError("observations_exceed_requested")
    repeats = defaultdict(dict)
    wording = defaultdict(dict)
    rankings = defaultdict(dict)
    tracks = Counter()
    for row in observations:
        tracks[row["track"]] += 1
        probe = catalog[row["probe_id"]]
        key = (row["case_id"], row["view_id"], row["probe_id"])
        if row["repeat"] in repeats[key]:
            raise ValueError("duplicate_case_view_probe_repeat")
        repeats[key][row["repeat"]] = row
        if probe.get("variant_group"):
            wording[(row["case_id"], row["view_id"], probe["variant_group"])][(probe["wording"], row["repeat"])] = row["decision"]["probability"]
        if probe.get("pair_actions"):
            rankings[(row["case_id"], row["view_id"], row["repeat"], probe["swap_group"])][row["probe_id"]] = row

    track_stats = {}
    for track in sorted(tracks):
        changes, variation, flips = [], [], 0
        for pair in repeats.values():
            if set(pair) != {0, 1} or pair[0]["track"] != track:
                continue
            a, b = pair[0]["decision"], pair[1]["decision"]
            if "probability" in a:
                pa, pb = a["probability"], b["probability"]
                changes.append(abs(pa - pb))
                flips += (pa >= .5) != (pb >= .5)
            else:
                da, db = a["probabilities"], b["probabilities"]
                variation.append(.5 * sum(abs(da[k] - db[k]) for k in da))
        track_rows = [r for r in observations if r["track"] == track]
        track_stats[track] = {"completed": len(track_rows), "source_texts": len({r["case_id"] for r in track_rows}),
            "complete_binary_repeat_pairs": len(changes), "mean_absolute_repeat_change": average(changes),
            "threshold_flips_at_0_5": flips, "complete_distribution_repeat_pairs": len(variation),
            "mean_total_variation_distance": average(variation)}

    matched = defaultdict(list)
    needed = {(w, r) for w in range(4) for r in (0, 1)}
    for (cid, view, concept), values in wording.items():
        if view != "original_full" or set(values) != needed:
            continue
        changes = [abs(values[w, 0] - values[w, 1]) for w in range(4)]
        spans = [max(values[w, r] for w in range(4)) - min(values[w, r] for w in range(4)) for r in (0, 1)]
        mixed = [len({values[w, r] >= .5 for w in range(4)}) > 1 for r in (0, 1)]
        matched[concept].append({"case_id": cid, "repeat_change": mean(changes),
                                 "wording_span": mean(spans), "mixed_threshold_repeats": sum(mixed)})
    by_concept = {}
    for concept, cells in sorted(matched.items()):
        by_concept[concept] = {"complete_source_groups": len(cells),
            "mean_absolute_repeat_change": mean(c["repeat_change"] for c in cells),
            "mean_within_repeat_wording_span": mean(c["wording_span"] for c in cells),
            "repeat_groups_with_mixed_threshold_decisions": sum(c["mixed_threshold_repeats"] for c in cells),
            "wording_repeat_groups": 2 * len(cells)}
    cells = [c for group in matched.values() for c in group]
    swap_count = stable = ambiguous = 0
    for group in rankings.values():
        if len(group) != 2:
            continue
        selected = []
        for row in group.values():
            probe = catalog[row["probe_id"]]
            label = unique_winner(row["decision"]["probabilities"])
            selected.append(probe["pair_actions"][0 if label == "A" else 1] if label in {"A", "B"} else label)
        swap_count += 1
        if None in selected:
            ambiguous += 1
        else:
            stable += selected[0] == selected[1]
    return {"requested": requested, "completed": len(observations),
        "coverage": len(observations) / requested if requested else None,
        "source_texts_observed": len({r["case_id"] for r in observations}), "by_track": track_stats,
        "matched_question_groups": {"complete_groups": len(cells), "distinct_source_texts": len({c["case_id"] for c in cells}),
            "mean_absolute_repeat_change": average([c["repeat_change"] for c in cells]),
            "mean_within_repeat_wording_span": average([c["wording_span"] for c in cells]), "by_concept": by_concept},
        "next_step_order": {"complete_swapped_pairs": swap_count, "stable_unique_winner_pairs": stable,
            "ambiguous_top_probability_pairs": ambiguous, "resolved_pairs": swap_count - ambiguous},
        "interpretation": "Descriptive behavior on observed source texts. No accuracy, legal finding or calibrated real-world risk claim."}


def style_summary(observations, references):
    lookup = {r["request_id"]: r for r in references}
    seen, condition, swaps = set(), defaultdict(list), defaultdict(dict)
    for row in observations:
        if set(row) != STYLE_FIELDS or row["request_id"] in seen or row["request_id"] not in lookup:
            raise ValueError("invalid_style_record")
        if row["winner"] not in {"A", "B", "tie"}:
            raise ValueError("invalid_style_winner")
        seen.add(row["request_id"])
        ref = lookup[row["request_id"]]
        condition[ref["method"].split(":")[0]].append(row["winner"] == ref["expected_winner"])
        winner = row["winner"]
        if ref["order"] == 1 and winner in {"A", "B"}:
            winner = "B" if winner == "A" else "A"
        swaps[ref["swap_group_id"]][ref["order"]] = winner
    pairs = [s for s in swaps.values() if set(s) == {0, 1}]
    correct = sum(sum(v) for v in condition.values())
    return {"requested": len(references), "completed": len(observations), "correct": correct,
        "conditional_accuracy": correct / len(observations) if observations else None,
        "coverage": len(observations) / len(references),
        "by_condition": {k: {"completed": len(v), "correct": sum(v), "accuracy": mean(v)} for k, v in sorted(condition.items())},
        "complete_swapped_pairs": len(pairs), "stable_swapped_pairs": sum(s[0] == s[1] for s in pairs),
        "interpretation": "Agreement with a constructed screening policy, not validated domain expertise."}


def reproduce(root):
    root = Path(root)
    spec = json.loads((root / "results/release_snapshot.json").read_text())
    output = {"schema": "duecare-public-findings/1.0.0", "snapshot_at": spec["snapshot_at"], "source_studies": {}, "style_judges": {}}
    for name, study in spec["source_studies"].items():
        catalog = json.loads((root / study["catalog"]).read_text())
        output["source_studies"][name] = source_summary(rows(root / study["observations"]), catalog, study["requested"])
    references = rows(root / "examples/style_comparison_references.jsonl")
    style_rows = {}
    for model, study in spec["style_judges"].items():
        style_rows[model] = rows(root / study["observations"])
        output["style_judges"][model] = style_summary(style_rows[model], references)
    common = set.intersection(*(set(r["request_id"] for r in values) for values in style_rows.values())) if style_rows else set()
    output["style_matched_intersection"] = {"requests": len(common), "judges": {
        model: style_summary([r for r in values if r["request_id"] in common], references)
        for model, values in style_rows.items()}}
    return output
