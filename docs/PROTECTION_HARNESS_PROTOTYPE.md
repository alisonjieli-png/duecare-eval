# Protection-first harness prototype

The prototype prepares a source-backed, structured request and checks the returned response object. It separates concern recognition, practical help and domestic criminal certainty. The current protocol is `duecare-protection-harness/2.1.0`.

Two bounded authored examples accompany the code: a worker-control case suited to ordinary explanation, and a document/wage-access concern with unresolved legal facts. Their supplied responses demonstrate the software contract. They are authored fixtures, with zero model generations or independently validated model answers.

## Executable components

| Component | What the code does | Remaining assessment |
| --- | --- | --- |
| Evidence selection | Checks pinned local bundles and retrieves scoped sources by declared topic IDs | New source discovery and applicability review |
| Fact slots | Validates caller-supplied actors, costs and access/control facts; retains their origin | Consistency with the full narrative and independent fact verification |
| Arithmetic | Uses decimal operands to reconcile totals, calculate declared simple interest and compare rates with matching units | Financial assumptions and legal applicability |
| Request contract | Requires concerns, practical actions, safe conditions, citations, missing facts and calibrated uncertainty | Whether generated advice actually meets those aims |
| Response checks | Checks identity, source/fact IDs, required actions and supplied action flags | Meaning, citation support and unmarked harmful instructions |

The source registry contains the dated ILO and domestic evidence packets, copied byte-for-byte with their hashes. A separate scope addendum records later checking of membership commitments and ratification. Existing benchmark inputs retain their original source versions.

The caller supplies structured facts explicitly. Words such as “trafficking” in free text do not create a concern signal. A declared wage or document restriction can support a concern while the prototype leaves domestic criminal certainty undetermined.

Rate comparison requires matching periods and bases. For example, a nominal annual rate and an effective annual threshold remain incomparable until the basis is clarified. A numerical comparison has its own result; the program makes no automatic legal classification from it.

## Practical help and uncertainty

The response contract requires at least one practical action. Qualified legal review can accompany protection, safe information gathering or ordinary help. A benign case can receive a clear explanation without escalation. An answer can abstain from a categorical legal conclusion while offering safe clarification or confidential support.

Every action carries safe conditions and declared fact/source references. Citation validation checks membership in the selected evidence set. Whether a passage supports a claim requires substantive review.

The caller may provide explicit coercive-collection flags, attributed to a user, reviewer or model. A positive supplied flag rejects the response contract; absent flags remain unassessed. The checker does not treat word matching or a model's declaration as proof of harm or safety. The negative fixture in the offline checker supplies a simulated flag to test that route, rather than asserting that the authored protective response recommends coercion.

## International and domestic scope

The `ilo.obligations` topic adds two source summaries and requires separate response notes for membership-based principles, ratified international obligations, territorial application and domestic implementation.

The ILO Declaration source describes Members' commitments to fundamental principles, including eliminating forced labour, whether or not they have ratified the relevant Conventions. The ratification source distinguishes accepted international obligations from domestic implementation gaps. A gap in implementation leaves the ratified obligation intact. These points differ from saying every state is bound by every detailed provision of every Convention. Individual applicability and domestic remedies still require the relevant facts. See the [dated scope addendum](../results/protection_harness_ilo_scope_v1_1.json) for the primary ILO links and exact supplied summaries.

## Run the examples offline

From the repository root, after installing the package:

```sh
python tools/check_protection_harness.py --check
python -m pytest tests/test_protection_harness.py
```

The checker reproduces two authored cases, four prepared request specifications, two valid authored responses and six rejection checks. It makes zero provider calls. Results and source hashes are in [the reproduction receipt](../results/protection_harness_checks_v2_1.json).

To prepare a request for a caller-owned hosted-model run:

```sh
python -m duecare_eval.protection_harness prepare --input examples/protection_harness/concern_input.json --mode harness --output concern_harness_request.json
python -m duecare_eval.protection_harness prepare --input examples/protection_harness/concern_input.json --mode bypass --output concern_bypass_request.json
python -m duecare_eval.protection_harness validate --prepared concern_harness_request.json --response examples/protection_harness/concern_authored_response.json
```

The bypass sends exactly the same full case as a user message and skips source retrieval, structured fact processing, arithmetic and the response contract. This compares the whole package, including the output format. Component-specific effects need additional matched contrasts.

The C context experiment remains a text-scaffold study. This executable prototype has its own version, examples and receipt. The private development workspace's 43 checks were software checks; this public package has 24 dedicated tests and reports its example coverage separately. Neither count measures model performance or independently validated worker protection.

For integration, `prepare(..., bundle_specs=...)` accepts explicit bundle paths and hashes. `validate_response(..., approved_sources=...)` accepts an already verified registry. Hosted generation, complete-answer review and independent legal, domain and worker-informed validation remain separately recorded steps.
