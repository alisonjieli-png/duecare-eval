"""Reproducible benchmark draws from a versioned graded library.

Each draw verifies the library digest, assigns whole corridor/indicator
families to calibration or held-out, and samples with a deterministic rule.
The same library, split, rule and size yield the same ordered items.

Comparisons over time also record judges, model versions and decoding settings.
This module handles the offline sampling step using local files.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from . import study_design as SD

SPLIT_PROTOCOL = "benchmark-split/1.0.0"
DRAW_PROTOCOL = "benchmark-draw/1.1.0"
SPEC_SCHEMA = "duecare-benchmark-spec/2.0.0"

CALIBRATION = "calibration"
HELD_OUT = "held_out"

#: Strata used for a balanced draw.
#:
#: Balance requested tier, length band, migration corridor and question template.
#: This gives each axis explicit coverage in a small draw. Target-capability
#: draws use the separate axes below because they assess the best safe response.
DEFAULT_STRATA = ("tier", "band", "corridor", "question")
TARGET_STRATA = ("band", "corridor", "question")


def sha256_file(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def stable_unit(seed: str, key: str) -> float:
    """Deterministic [0,1) draw for a key. Same seed and key, same value, always."""
    return int(hashlib.sha256(f"{seed}\x00{key}".encode("utf-8")).hexdigest()[:16], 16) / 2 ** 64


def group_key(item: dict) -> str:
    """The leakage unit: an indicator family inside a migration corridor.

    Chosen so that two items sharing it are variants of the same underlying
    judgement. Splitting below this level would put near-duplicates on both
    sides of the split.
    """
    axes = item["axes"]
    return f"{axes['corridor']}|{axes['indicator']}"


def verify_library(library_path, manifest_path) -> dict:
    """Return the manifest after checking its digest against the library file."""
    library_path, manifest_path = Path(library_path), Path(manifest_path)
    if not library_path.exists():
        raise FileNotFoundError(f"library_missing:{library_path.name}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    actual = sha256_file(library_path)
    expected = manifest.get("file_sha256")
    if actual != expected:
        raise ValueError(
            f"library_digest_mismatch: manifest says {expected}, file is {actual}. "
            "The item set changed after the manifest was written; rebuild both "
            "or point --manifest at the matching one.")
    return manifest


def assign_splits(groups, holdout_fraction: float = 0.3, seed: str = "20260928") -> dict:
    """Assign whole families to calibration or held-out.

    Deterministic on the group key, so the split is stable as the library grows
    and identical for every reader of the same spec. Fraction is approximate by
    construction: the hash threshold assigns each group independently of the
    other groups and their sizes.
    """
    if not 0.0 < holdout_fraction < 1.0:
        raise ValueError("holdout_fraction_out_of_range")
    return {g: (HELD_OUT if stable_unit(seed, g) < holdout_fraction else CALIBRATION)
            for g in sorted(set(groups))}


def _seeded_shuffle(items: list, seed: str) -> list:
    """Deterministic shuffle.

    `random.shuffle` is stable for a fixed seed, but sorting by a keyed hash is
    stable across interpreter versions and platforms too, which matters because
    a published draw has to be reconstructible from its own spec.
    """
    return sorted(items, key=lambda s: (stable_unit(seed + "\x00order", s), s))


def stratum_of(item: dict, axes=DEFAULT_STRATA) -> str:
    a = item["axes"]
    return "|".join(str(a[name]) for name in axes)


def draw(items, size: int, seed: str, axes=None,
         holdout_only: bool = True, splits: dict = None,
         evaluation_mode: str | None = None) -> dict:
    """Balanced, deterministic draw.

    Items are bucketed by stratum, ordered within a bucket by a seeded hash of
    the item id, then dealt round-robin across buckets until `size` is reached.
    Round-robin over strata is what makes a small draw still representative; a
    proportional slice would quietly under-sample rare corridors.

    The selected item IDs have a digest that lets readers verify the draw.
    """
    if size <= 0:
        raise ValueError("draw_size_must_be_positive")
    if evaluation_mode is not None and evaluation_mode not in SD.EVALUATION_MODES:
        raise ValueError(f"unknown_evaluation_mode:{evaluation_mode}")
    axes = tuple(axes or (
        TARGET_STRATA if evaluation_mode == SD.TARGET_CAPABILITY else DEFAULT_STRATA
    ))
    pool = []
    for item in items:
        if evaluation_mode is not None and not SD.eligible_for_mode(item, evaluation_mode):
            continue
        if holdout_only:
            if splits is None:
                raise ValueError("held_out_draw_requires_splits")
            if splits.get(group_key(item)) != HELD_OUT:
                continue
        pool.append(item)
    if not pool:
        raise ValueError("no_items_in_split")

    buckets: dict[str, list] = {}
    for item in pool:
        buckets.setdefault(stratum_of(item, axes), []).append(item)
    for key in buckets:
        buckets[key].sort(key=lambda it: (stable_unit(seed, it["item_id"]), it["item_id"]))

    # Shuffle bucket order as well as items. Lexicographic stratum keys place
    # tier-1 buckets first, which biases draws smaller than the bucket count.
    # The seeded order keeps every draw reproducible.
    order = sorted(buckets)
    order = _seeded_shuffle(order, seed)

    chosen, cursor = [], {k: 0 for k in order}
    while len(chosen) < size and any(cursor[k] < len(buckets[k]) for k in order):
        for key in order:
            if len(chosen) >= size:
                break
            i = cursor[key]
            if i < len(buckets[key]):
                chosen.append(buckets[key][i])
                cursor[key] = i + 1
    if len(chosen) < size:
        raise ValueError(f"draw_exceeds_pool: asked {size}, split holds {len(pool)}")

    ids = [it["item_id"] for it in chosen]
    return {
        "protocol": DRAW_PROTOCOL,
        "requested": size,
        "drawn": len(chosen),
        "strata_axes": list(axes),
        "strata_count": len(buckets),
        "seed": seed,
        "holdout_only": holdout_only,
        "evaluation_mode": evaluation_mode,
        "reference_basis": (SD.reference_basis(evaluation_mode)
                            if evaluation_mode is not None else None),
        "pool_size": len(pool),
        "item_ids": ids,
        "draw_sha256": hashlib.sha256("\n".join(ids).encode("utf-8")).hexdigest(),
        "stratum_counts": {k: sum(1 for it in chosen if stratum_of(it, axes) == k)
                           for k in sorted({stratum_of(it, axes) for it in chosen})},
    }


def build_spec(*, label: str, manifest: dict, draw_result: dict, splits: dict,
               holdout_fraction: float, split_seed: str, targets, judges,
               decoding: dict = None, arms=None, notes: str = "",
               evaluation_mode: str = SD.TARGET_CAPABILITY,
               design_coverage: dict | None = None,
               validation: dict | None = None,
               system_arms: list | None = None,
               instrument_audit: dict | None = None,
               measurement_acceptance: dict | None = None,
               reference_arrays: dict | None = None,
               domain_pack: dict | None = None) -> dict:
    """The frozen, publishable description of one benchmark run.

    Record the settings needed to compare two runs. Put unresolved settings,
    such as a service-controlled model version, in the notes field.
    """
    if evaluation_mode not in SD.EVALUATION_MODES:
        raise ValueError(f"unknown_evaluation_mode:{evaluation_mode}")
    reference = SD.reference_basis(evaluation_mode)
    declared_arms = arms or []
    return {
        "schema": SPEC_SCHEMA,
        "label": label,
        "evaluation_mode": evaluation_mode,
        "reference": {
            "basis": reference,
            "target_grade": 5 if evaluation_mode == SD.TARGET_CAPABILITY else None,
            "note": (
                "Target capability is compared with the evidence-derived ideal grade."
                if evaluation_mode == SD.TARGET_CAPABILITY else
                "Requested tiers are used only to calibrate a generator or judge; "
                "they are not target-model ground truth."
            ),
        },
        "library": {
            "protocol": manifest.get("protocol"),
            "taxonomy_version": manifest.get("taxonomy_version"),
            "file_sha256": manifest["file_sha256"],
            "items_available": manifest.get("items_written"),
            "label_basis": reference,
            "model_generated": manifest.get("model_generated"),
            "artifact_classification": manifest.get("artifact_classification"),
            "study_design": manifest.get("study_design", SD.KAGGLE_DESIGN_VERSION),
            "note": (
                "The library retains its full five-tier constructed ladder for calibration. "
                "Target capability draws use only the canonical best-answer reference; "
                "requested tiers are never treated as target-model truth."
            ),
        },
        "split": {
            "protocol": SPLIT_PROTOCOL,
            "unit": "corridor|indicator",
            "seed": split_seed,
            "holdout_fraction": holdout_fraction,
            "families_total": len(splits),
            "families_held_out": sum(1 for v in splits.values() if v == HELD_OUT),
            "families_calibration": sum(1 for v in splits.values() if v == CALIBRATION),
            "split_sha256": hashlib.sha256(
                "\n".join(f"{k}={v}" for k, v in sorted(splits.items())).encode("utf-8")
            ).hexdigest(),
        },
        "draw": {k: v for k, v in draw_result.items() if k != "item_ids"},
        "targets": targets,
        "judges": judges,
        "arms": declared_arms,
        "system_arms": system_arms or [],
        "design": {
            "profile": "amarel_kaggle_full_scope",
            "lineage": SD.KAGGLE_DESIGN_VERSION,
            "failure_family_coverage": design_coverage or {},
            "four_arm_audit": SD.four_arm_audit(system_arms or []),
        },
        "validation": validation or {},
        "instrument_audit": instrument_audit or {},
        "reference_arrays": reference_arrays or {},
        "domain_pack": domain_pack or {},
        "measurement_acceptance": measurement_acceptance or {
            "minimum_judge_coverage": 0.95,
            "minimum_krippendorff_alpha_ordinal": 0.67,
            "agreement_policy": (
                "Below 0.67, do not aggregate the panel into a comparative score; "
                "route disagreement to review."
            ),
        },
        "resource_plan": SD.call_estimate(
            int(draw_result.get("drawn", 0)), len(targets),
            len(declared_arms or ["bare"]), len(judges)),
        "decoding": decoding or {},
        "notes": notes,
        "comparability": (
            "A later run is comparable to this one only if library file_sha256, "
            "split split_sha256, draw draw_sha256, targets, judges, arms and "
            "decoding all match. Any change is a new benchmark version, not a "
            "re-measurement."),
    }
