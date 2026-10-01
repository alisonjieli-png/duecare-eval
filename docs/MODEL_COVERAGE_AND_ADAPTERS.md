# Model coverage and serving controls

Six additional hosted model configurations answered the same five source cases in two conditions: the original question alone and the original question with a dated evidence packet. The collection finished on October 1, 2026 at 00:04:46 UTC. It contains 60 requested answer slots, 46 complete responses and 14 truncated responses. Every requested slot has a recorded outcome.

Those are five underlying cases: four exact published advice prompts and one complete, separately identified notebook variant. The notebook variant's identity with the truncated exhibit in the original write-up remains unproven. The [source bank](../examples/reference_bank_v1/cases.json) retains the prompt strings and their hashes.

## What each count means

A catalog listing identifies an advertised route. A successful access probe records a response from that route. A complete response has nonempty recorded text, an exact requested/returned model-tag match and a completed provider finish, within the output allocation. A behavior assessment examines what the answer recognizes, recommends and gets wrong. Each of these is a separate evidence state.

| Requested hosted model | Answer slots | Complete | Truncated |
|---|---:|---:|---:|
| `glm-5.3` | 10 | 2 | 8 |
| `glm-5.3-flash` | 10 | 4 | 6 |
| `gpt-oss:120b` | 10 | 10 | 0 |
| `minimax-m3` | 10 | 10 | 0 |
| `mistral-large-3:675b` | 10 | 10 | 0 |
| `nemotron-3-ultra` | 10 | 10 | 0 |
| Total | 60 | 46 | 14 |

Each model's denominator is five cases times two context conditions. All six short access probes completed. The original collection used 82 physical calls, including those probes and 16 second attempts. Every call has a recorded outcome. Hosted model tags identify the reported deployment; an immutable weight revision remains unavailable.

The [collection snapshot](../results/model_expansion_2026-10-01.json) was captured at 00:09:50 UTC, before the later worker-help reviews. Its behavior-assessed count is therefore zero. The [subsequent worker-help review](../results/new_models_worker_help_review_2026-10-01.json) assesses all ten complete answers among twelve requested answers to that one case. Two truncated answers remain unscored. These are automated assistant assessments; independent worker and domain review remain open.

## GLM's supported reasoning setting

Both GLM deployments advertise `low`, `high` and `max` reasoning, with `max` as their default. The initial collection requested `think: false`, which is absent from those advertised controls. The effective reasoning level of those initial calls is unverified. The [Ollama thinking documentation](https://docs.ollama.com/capabilities/thinking) describes choosing an exact supported level returned by `/api/show`.

A separate two-call experiment used `think: "low"`. Each GLM answered the same original salary-deduction question, with the same messages, temperature and 8,192-token limit. Both initial responses to that question had truncated; both low-effort responses completed, with reasoning and final content in separate provider fields. The two follow-up observations retain their own IDs and hashes. The original 46-complete/14-truncated totals stay intact.

This establishes a useful serving-control result for one case on two deployments. The [targeted reading of their final answers](../results/glm_low_control_reading_2026-10-01.json) also identifies legal-rule errors. Completion and sound advice still require separate checks.

## OpenCode discovery and diagnostics

The [inventory](../results/model_inventory_2026-10-01.json) records 62 advertised CLI routes: 24 under `ollama-cloud`, 29 under `opencode-go`, eight under `opencode` and one under `tactical`. A separate hosted Ollama catalog contained 17 model tags. These inventories have different scopes; a listed model's inference access needs its own observation.

Two tools-disabled CLI diagnostics selected `opencode-go/qwen3.8-flash`. Each stopped before an answer. The second captured `UnknownError` with the message “Unexpected server error. Check server logs for details.” The evidence establishes two CLI invocations. Internal provider-call counts, served identity and the underlying error cause remain unknown. These diagnostics measure the attempted CLI deployment, with Qwen answer quality awaiting a successful response.

## Scale of the broader runs

The 32-response context/scaffold comparison is one small, matched experiment within a larger program. The [native-call accounting snapshot](../results/native_call_accounting_2026-10-01.json), captured October 1 at 02:38:18–02:38:22 UTC, contains 84,359 non-Jev hosted-call attempt reservations across the selected campaigns. Of these, 84,349 have recorded outcomes and ten remain open. Attempts include grading, repeated conditions, retries and unsuccessful responses. The six CLI invocations in this audit have their own accounting because their internal provider-call counts are unknown.

At that capture, the bulk Tactical lane had 16,421 completed generations among 20,080 requested. Its separate variation lane had completed 4,320 of 4,320. The two style judges supplied 3,456 completed comparisons from 3,458 attempts. The 74,640 archived prompt strings describe the source inventory; call evidence comes from journals. Each published journal-prefix hash fixes the records included in this selected-campaign audit while ongoing work continues.

GLM 5.3 already has 49 recorded attempts in the newest five-experiment bundle: 20 in the source-answer/access-check study, 16 in the matched-context study, twelve in the adapter study and one in the separate low-effort source-case check. GLM 5.3 Flash has 43 in that bundle, plus earlier judge and comparison work. Their reported model IDs and request conditions are part of the evidence.

## Refreshed availability and local classification

The [metadata-only availability check](../results/model_availability_2026-10-01.json) at 02:43:28 UTC found the same 17 hosted Ollama tags and 62 CLI catalog routes. Hosted candidates outside the current eleven text-model comparison include `deepseek-v4-pro:0813`, `glm-5.2`, `minimax-m2.7`, `nemotron-3-super`, `nemotron-3-nano:30b`, `kimi-k2.6` and `kimi-k2.7-code`. Their catalog presence is recorded; a future inference test would establish access and performance under a declared condition.

The installed Ollama catalog contains six entries with different execution roles:

| Installed entry | Metadata classification | Project execution scope |
|---|---|---|
| GLM 5.3 Flash, GLM 5.2, DeepSeek V4 Flash 0731 and Kimi K2.7 Code cloud aliases | Four small alias records point to hosted Ollama models. The GLM 5.3 Flash alias is 317 bytes. | Hosted inference remains distinct from local weight execution. |
| `qwen2.5-coder:7b` | Local generative weights; reported 7.6B parameters and about 4.68 GB. | The project's local-LLM execution prohibition applies. |
| `nomic-embed-text:latest` | A 137M-parameter embedding model, about 274 MB. | Small local embeddings have separate permission; they supply embeddings rather than full advice answers. |

This availability pass made metadata requests and dispatched zero inference requests. It downloaded no model weights and changed no running controller or account configuration.

## Proposed decision-model and classifier comparisons

TypeSafe's documented hosted model is `jev-1.13.0`, with text input, a 64k total request budget and a 32k limit for state plus the longest question. Its documentation places domain customization in the request's state, instructions and criteria, with atomic questions combined in code. An official open-weight Jev release remains unverified in this review. [TypeSafe model documentation](https://docs.typesafe.ai/models).

OpenJev is an independent, Qwen-based 27B typed-decision model. Its model card describes choice, yes/no probability and score outputs; it lists CC BY-NC 4.0 weights and Apache 2.0 helper/serving code. The Hugging Face Inference Providers section lists no serving provider. A hosted deployment, license fit and data-handling review are therefore part of preparing a DueCare comparison. OpenJev has no DueCare inference result in this snapshot. [OpenJev model card](https://huggingface.co/openjev/openjev).

`MoritzLaurer/ModernBERT-large-zeroshot-v2.0` is a separate 0.4B text-classification candidate under Apache 2.0. Its model card lists HF Inference API support; account-specific access remains untested here. A classifier adapter would need explicit label semantics, input-length checks and calibrated thresholds before its outputs could join the benchmark. [ModernBERT classifier card](https://huggingface.co/MoritzLaurer/ModernBERT-large-zeroshot-v2.0).

A useful next comparison would retain the full source cases and assess source-linked Palermo components, ILO warning signs and remedy priorities separately. Include benign controls, evidence sufficiency and worker-choice questions. Test option-order stability and calibration before combining scores. New remote providers require a privacy review before they receive restricted responses; all proposed candidates retain separate model, provider, license and method identities.

## Reproduce the records offline

From the public checkout:

```sh
python tools/reproduce_model_expansion.py --check
python tools/reproduce_model_expansion.py
```

The checker reconstructs all 60 original request payloads, six access-probe payloads and two low-effort payloads from the public source prompts and evidence packet. Their SHA-256 digests must match the recorded requests. It also checks the full model/case/condition grid, stable IDs, served tags, retry history, output limits, coverage totals, separate follow-up linkage and CLI uncertainty fields.

Full model responses and private journals remain restricted. Their public digests support linkage and integrity checks; this checker recomputes the request bytes and coverage, while treating restricted response-byte hashes and all-attempt token totals as recorded provenance. The [main report](PAPER.md) pairs these counts with case-specific findings and response evidence.
