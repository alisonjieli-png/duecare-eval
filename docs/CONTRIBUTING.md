# Reproduce and improve the benchmark

Start with the versioned release, its paper and `results/release_snapshot.json`. Run `duecare-eval doctor` to check the local files, then `python tools/reproduce_findings.py --check` before interpreting differences. The public tools reproduce the released aggregates offline from the included numeric evidence.

## Report a result discrepancy

Include the release tag, Python version, command, request or question ID, expected result and observed result. Explain whether the discrepancy concerns source meaning, a reference label, extraction, aggregation or presentation. A small numeric example is usually more useful than an entire log.

Use the repository's public examples to build a reproducible issue. Keep credentials, identifying worker information, private notebooks, restricted response banks and raw provider journals in their authorized storage.

## Propose a new comparison

State the question, source provenance, visible information, output contract, sampling unit, reference assumptions and planned analysis. Preserve an original text digest and document adaptations. Keep all related variants in the same evaluation split. Record the requested denominator, including missing and invalid outputs.

Different wording can change the proposition. Explain which changes should preserve the answer, which should change it, and why. For rankings, map candidate positions back to identity. For probability outputs, distinguish repeatability, discrimination, calibration and the decision threshold.

Source grades, requested generation tiers and assessed grades have separate fields. Treat consensus and similarity as measurements, and justify correctness labels with explicit references and review. Case review should preserve practical worker choices and distinguish a concern from an established legal conclusion.

## Check a code change

Run the offline tests and the findings reproduction command. Changes to an executed protocol need a new version. Preserve the observations and references used by earlier runs, and make any correction traceable to its source. Numerical or methodological corrections should identify the affected claims and retain the prior release for comparison.

Useful contributions include reproducible failures, null findings, clearer references and improved coverage. Public cases use reviewed research material that protects people's identities.
