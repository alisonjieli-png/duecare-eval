# Full text without public disclosure

Benchmark fidelity and public disclosure are different decisions. The original source texts remain intact in the private archive. The released bounded fixtures and newly generated variants are separately versioned derivatives, not verbatim replications. Scores from those protocols must not be merged silently.

The optional `duecare_eval.vault` module supports authenticated encryption at rest and exact-byte decryption for a trusted local comparison. Install the `vault` extra. Supply a 32-byte key from an approved secret manager; never commit, log, embed or transmit that key with the encrypted fixture. `seal` generates a fresh nonce for each envelope. `open_in_memory` authenticates before exposing plaintext. `compare_locally` permits only a small fixed set of finite numeric metrics in its receipt and uses a keyed source fingerprint.

This follows the [cryptography AES-GCM API](https://cryptography.io/en/latest/hazmat/primitives/aead/). Encryption is not encoding, and neither changes whether a disclosure or an evaluation is authorized. No encrypted historical dataset or decryption key is distributed in this release.

Important boundaries:

- The helper itself performs no file or network I/O. The evaluator is trusted application code, not sandboxed by this API.
- Ordinary Python cannot guarantee zeroization of all plaintext copies, exclusion from swap, core dumps, diagnostics, or malicious callback logging. A stronger memory-only threat model needs OS/process isolation and review.
- Calling a remote model sends plaintext to that provider. Encryption at rest cannot establish provider non-retention or override the dataset's approved-recipient policy.
- Existing campaign journals may retain plaintext. Do not reuse them for a new full-text in-memory protocol and describe the result as metadata-only.
- Existing private plaintext archives have not been deleted or retroactively encrypted. Production key management and a protected-runtime deployment remain separate work.
- Full-text fidelity does not validate a source's legal claims or original quality ratings. Labels still require independent assessment.

The tests verify exact-byte round trips, fresh ciphertext, authentication failure for wrong keys or tampering, and rejection of textual receipts. They do not claim secure-enclave isolation or remote-provider privacy guarantees.
