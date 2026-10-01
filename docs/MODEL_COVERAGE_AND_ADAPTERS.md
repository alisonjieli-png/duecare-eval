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

## Reproduce the records offline

From the public checkout:

```sh
python tools/reproduce_model_expansion.py --check
python tools/reproduce_model_expansion.py
```

The checker reconstructs all 60 original request payloads, six access-probe payloads and two low-effort payloads from the public source prompts and evidence packet. Their SHA-256 digests must match the recorded requests. It also checks the full model/case/condition grid, stable IDs, served tags, retry history, output limits, coverage totals, separate follow-up linkage and CLI uncertainty fields.

Full model responses and private journals remain restricted. Their public digests support linkage and integrity checks; this checker recomputes the request bytes and coverage, while treating restricted response-byte hashes and all-attempt token totals as recorded provenance. The [main report](PAPER.md) pairs these counts with case-specific findings and response evidence.
