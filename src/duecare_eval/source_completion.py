"""Validate the final requested source population and supplemental provenance."""
from collections import Counter
from hashlib import sha256
import gzip
import json
from pathlib import Path
import re

from .longform_annotations import digest, probability
from .source_analysis import validate_source

FIELDS = {"request_id", "case_id", "probe_id", "view_id", "repeat", "track", "model", "original_status", "status",
          "observation_source", "decision", "request_sha256", "selected_receipt_sha256", "original_receipt_sha256"}


def assess(records, catalog):
    seen, usable = set(), []
    known_probes = {p["probe_id"] for p in catalog}
    for row in records:
        if set(row) != FIELDS or row["request_id"] in seen:
            raise ValueError("unknown_fields_or_duplicate_source_request")
        seen.add(row["request_id"])
        if (row["probe_id"] not in known_probes or row["model"] != "jev-1.13.0" or not digest(row["case_id"])
                or type(row["repeat"]) is not int or row["repeat"] not in (0, 1)
                or row["track"] not in {"source_context", "perspective_expansion"}
                or re.fullmatch(r"SRCQ-[a-f0-9]{26}", row["request_id"]) is None):
            raise ValueError("unknown_source_request_metadata")
        if row["status"] not in {"completed", "provider_error"} or row["original_status"] not in {"completed", "provider_error"}:
            raise ValueError("unexpected_source_outcome")
        if row["observation_source"] not in {"primary", "terminal_supplement", "mass_diagnostic_strictly_accepted"}:
            raise ValueError("unknown_source_observation_origin")
        if not all(digest(row[k]) for k in ("request_sha256", "selected_receipt_sha256", "original_receipt_sha256")):
            raise ValueError("invalid_source_provenance_digest")
        if row["observation_source"] == "primary":
            if row["status"] != row["original_status"] or row["selected_receipt_sha256"] != row["original_receipt_sha256"]:
                raise ValueError("primary_outcome_relabelled")
        elif row["original_status"] != "provider_error" or row["status"] != "completed":
            raise ValueError("invalid_supplement_overlay")
        if row["status"] == "completed":
            probabilities = row["decision"].get("probabilities") if isinstance(row["decision"], dict) else None
            if probabilities is not None:
                if not isinstance(probabilities, dict) or not all(probability(v) for v in probabilities.values()):
                    raise ValueError("invalid_source_probability_values")
                if abs(sum(probabilities.values()) - 1) > 1e-4:
                    raise ValueError("strict_source_probability_mass")
            usable.append({k: row[k] for k in ("request_id", "case_id", "probe_id", "view_id", "repeat", "track", "model", "decision", "request_sha256")})
        elif row["decision"] is not None:
            raise ValueError("failed_outcome_has_decision")
    validate_source(usable, {p["probe_id"]: p for p in catalog})
    return {"requested": len(records), "primary_usable": sum(r["original_status"] == "completed" for r in records),
        "primary_errors": dict(Counter(r["original_status"] for r in records)),
        "supplemental_usable": sum(r["observation_source"] != "primary" for r in records),
        "combined_usable": len(usable), "remaining_unusable": len(records) - len(usable),
        "by_track": {name: {"requested": sum(r["track"] == name for r in records),
            "primary_usable": sum(r["track"] == name and r["original_status"] == "completed" for r in records),
            "combined_usable": sum(r["track"] == name and r["status"] == "completed" for r in records)} for name in sorted({r["track"] for r in records})},
        "observation_sources": dict(Counter(r["observation_source"] for r in records if r["status"] == "completed"))}


def reproduce(root):
    root = Path(root)
    summary = json.loads((root / "results/source_completion_2026-09-30.json").read_text())
    data = (root / "results" / summary["data"]["file"]).read_bytes()
    if sha256(data).hexdigest() != summary["data"]["sha256"]:
        raise ValueError("source_completion_file_digest_mismatch")
    catalog_bytes = (root / summary["catalog"]["file"]).read_bytes()
    if sha256(catalog_bytes).hexdigest() != summary["catalog"]["sha256"]:
        raise ValueError("source_catalog_digest_mismatch")
    expanded = gzip.decompress(data)
    if len(expanded) != summary["data"]["decompressed_bytes"]:
        raise ValueError("source_data_size_mismatch")
    records = [json.loads(line) for line in expanded.splitlines() if line.strip()]
    counts = assess(records, json.loads(catalog_bytes))
    if counts != {k: summary[k] for k in counts} or len(records) != summary["data"]["rows"]:
        raise ValueError("source_completion_count_mismatch")
    return counts
