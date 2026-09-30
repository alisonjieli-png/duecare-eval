# Roadmap from a working core to stronger evidence

## Published core

The offline CLI validates and scores 937 released decision fixtures. The released Jev numeric responses reproduce the published aggregate exactly. The public comparison fixture contains 1,728 cases with ties and non-tie controls. The README and PDF report a dated, preliminary snapshot rather than the eventual outcome of running jobs.

The headline finding is narrow and testable: at the declared 0.5 threshold, Jev accepted all 13 arithmetic claims, including seven deliberately false claims. In the same constructed suite it correctly handled 576 of 576 explicit action-boundary tasks. These observations motivate further testing, not a general verdict on the model.

## Next experiments

| Priority | Improvement | Required evidence before claiming success |
|---|---|---|
| 1 | Replicate arithmetic and test calibration | Predeclare balanced claims, varied numbers, question polarity and context layouts. Separate ranking from decision thresholds. Fit calibration only on a distinct development set, then test held-out cases. |
| 2 | Complete matched cross-model comparisons | Run the same frozen tasks under declared interfaces; report full coverage and matched intersections, not rankings of different partial subsets. |
| 3 | Assess the larger answer arrays | Finish the 20,080-candidate run and 4,320-candidate supplement. Measure requested-versus-assessed tier, refusal, distinctness, length and format adherence. |
| 4 | Validate the judges | Use corrected mixed style controls, swapped positions and multiple model families. Exclude earlier label-cued diagnostics from validity claims. Obtain independent human judgments. |
| 5 | Test improvement over time | Freeze a held-out suite, record served versions and decoding settings, repeat on later versions and use paired, group-based comparisons. No improvement or regression claim is supported yet. |
| 6 | Review domain validity | Independent legal/domain adjudication, affected-worker input and native-language review. Explicitly distinguish a concern from a legal finding. |
| 7 | Deploy a protected full-text workflow | Approve recipients and key management, audit evaluators and journals, test OS/process controls and preserve exact texts. The current helper is not a secure enclave or provider-retention guarantee. |
| 8 | Finalize rights and publication packaging | Select a licence, review third-party source rights, extend the reproducibility package and publish a versioned report when evidence changes. |

## Release discipline

Do not modify a running protocol invisibly. New text, formatting, evidence, scoring rules or label corrections require a new identifier and transformation record. Preserve failed and missing outcomes. Keep original, transformed and synthetic task families separate. Nothing in this roadmap authorizes contacting real workers or deploying a decision system without the stated review.
