# Educational red teaming and text fidelity

This project examines model behavior on fictional safeguarding scenarios and controlled evaluation tasks. It is educational red-teaming research, not operational advice, an investigative tool, a worker-risk assessment service, legal guidance, or a deployment certification. A deficient answer in the dataset is an object of study, not an endorsement.

## Keep the comparison valid

Three representations must remain distinct:

1. **Verbatim source:** exact original text with its provenance. The private source archive is preserved. Its supplied labels are not automatically correct.
2. **Bounded derivative:** a changed prompt with its own protocol identifier and declared changes. Shortening, abstraction or redaction can alter intent and difficulty. Results do not retroactively describe the original text.
3. **Synthetic policy fixture:** an authored case with an explicit expected outcome under a stated policy. This is constructed ground truth, not independent human adjudication of a real case.

Generation and grading must use the same case text and evidence. A new rewrite must never inherit an old grade silently. Changes to actor, intent, consent, chronology, money, debt, threats, control, jurisdiction or uncertainty require re-review. Preserve an original digest and a transformation record. Do not treat whitespace, translation, encoding or paraphrase as universally meaning-preserving.

The public style-equivalence tests stipulate equivalence under a narrow fictional policy. Their ties measure compliance with that policy. They are not a claim that technically dense and simple wording always have equal utility for a particular reader. Quality and usability must be assessed separately.

The current corpus primarily evaluates English. No native-language, legal, affected-worker or independent human validity is inferred from software tests or agreement between models. A model family's repeated votes do not establish independent corroboration.

## Data handling

Do not publish identifying details, real worker records, private attachments, credentials or restricted raw outputs. Encryption protects storage; it does not authorize disclosure or remove the need to review a recipient and evaluator. Local decrypt-in-memory tooling is not proof that an OS, callback or external provider cannot retain text. See FULL_TEXT_EVALUATION.md.

Operationally enabling legacy material remains private. The public release uses bounded synthetic cases and aggregate or numeric outputs. Reference errors, missing outputs, refusals, disagreements and failed tests should remain visible. This release makes no universal model ranking or claim that Jev can safely handle real cross-border cases without qualified human involvement.
