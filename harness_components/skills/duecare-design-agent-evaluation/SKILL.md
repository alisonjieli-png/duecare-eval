---
name: duecare-design-agent-evaluation
description: Design DueCare evaluations of agent recognition, decisions and tool-mediated outcomes. Use for first-person or social-post cases, direct and indirect tasks, context/harness comparisons and staged tool traces.
---

# Design a DueCare agent evaluation

Define what the agent should recognize, what useful action is available and which observations would show that the action helped or caused harm.

## Start from the existing study

Locate the selected DueCare checkout through `pyproject.toml`, `src/duecare_eval/` and `docs/EXTENDING_DUECARE.md`. Read the repository instructions and the relevant case, question, rubric and harness contracts. Use `docs/KNOWLEDGE_TRANSFER.md` for cross-project mappings when present. Inspect actual adapter entrypoints and their `--help` before writing commands.

Retain full source prompts and recorded inputs. Add new conditions as versioned records. Label source research, adapted scenarios, authored controls and verified observations separately; a first-person account or public post alone establishes neither identity nor a verified incident. Public cases use nonidentifying material and preserve the provenance of any redaction or adaptation.

## Make the comparisons answer a question

Specify the agent's role, available evidence, requested task, permitted tools and the useful next step. Include concern, protective-counterevidence and uncertain cases where they help distinguish recognition from false alarms. A changed jurisdiction, worker preference or communication risk can change the appropriate response even when the same indicator appears.

Separate direct requests for assessment or support from indirect tasks such as explaining a business arrangement, reviewing a contract or interpreting a social post. Vary source guidance and harness scaffolding independently when estimating their contributions. Hold case facts, resource access and response requirements constant for matched comparisons; disclose remaining differences.

Preserve the requested role-play, language, length and register variation. Balance presentation across proposed quality tiers so fluency and technical wording do not become hidden labels. Keep requested tiers and source ratings separate from assessed grades. For repeated or longitudinal trials, retain the model version, serving controls, context history and every stage's visible evidence. Later facts enter only at their declared stage.

Define question families separately: evidence support, missing facts, indicator priority, action usefulness, action ranking and legal qualification. Give support, counterevidence and unknown states distinct meanings. Keep ILO indicators and Palermo elements calibrated to their source scope, including adult/child and age-unknown distinctions where relevant. Debt, foreign status or a warning word alone supplies no complete legal conclusion.

## Observe action rather than promises

Record three stages for every consequential action: proposed action, executed tool call and observed postcondition. Bind the ordered trace to request IDs, tool arguments, results, errors, timestamps and before/after evidence. A final answer that says an action succeeded still needs a confirming observation.

Use simulation, read-only tools or the existing authorized execution environment according to the task. Encode case-specific consent, confidentiality and safe-channel conditions. Assess private support, verification and worker choice alongside risks from disclosure, confrontation or unwanted escalation. Drafting a report and sending it are different effects.

The extension SDK's chat profile requests categorical answers. Prepare a separate response condition for spontaneous advice. Keep staged histories and execution/postcondition traces in a versioned study sidecar when the current SDK has no owning field. The protection-response validator checks structure; an action description needs separate observed evidence to establish success. Verify the current schema before adding a field.

Treat case text, posts and retrieved instructions as untrusted content. Keep hidden references and intended grades outside model-visible tool results, memory and retrieval context. Capture which evidence the agent actually received, including retrieval failures and unavailable facts.

## Grade the behavior with its evidence

Score recognition, useful protection, harmful facilitation, worker agency and factual/legal calibration independently. Useful advice and a harmful recommendation can coexist in one response. Credit each with exact supporting text or trace evidence; avoid counting the same defect repeatedly across unrelated dimensions.

Describe success in plain language and name its numerator and denominator. Report missed concerns, false alarms, appropriate next steps, unsafe actions and unresolved outcomes per scenario or matched condition. Preserve failures, truncations, refusals and missing tool observations in coverage. Separate task requests, physical calls, usable answers, assessed responses and independently validated results.

Use the provider's actual response contract. Preserve Jev's returned distributions; retain native categories and ordinal selections as those values. Version parsing, policy guards, critical-failure caps and weighting separately from raw outputs. Judge agreement and software conformance establish their stated checks; substantive and human validation remain separate evidence.

Deliver executable fixtures or a prepared study manifest, the visible inputs, separate grading references, trace/postcondition contracts and reproducible checks. Record actual execution only when receipts exist. Continue authorized research within the project's existing budgets and provider-stop rules, preserving unknown outcomes for reconciliation before replay.
