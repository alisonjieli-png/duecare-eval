# Exact text and controlled access

DueCare preserves original source texts in the private archive and versions each adapted task separately. Evaluations use the exact text associated with their protocol. Reports identify which version produced each score and document any analysis that combines versions.

The optional `duecare_eval.vault` module supplies authenticated encryption at rest and exact-byte decryption for a trusted local comparison. Install the `vault` extra. Supply a 32-byte key from an approved secret manager and keep it separate from the encrypted fixture, source tree and logs. `seal` generates a fresh nonce for each envelope. `open_in_memory` authenticates before exposing plaintext. `compare_locally` accepts a fixed set of finite numeric metrics in its receipt and uses a keyed source fingerprint.

The helper uses the [cryptography AES-GCM API](https://cryptography.io/en/latest/hazmat/primitives/aead/). Dataset access and evaluation still require the appropriate authorization. This release distributes the helper and its tests; historical datasets and keys remain in their authorized private storage.

Responsibilities around the helper:

- The calling application controls file and network I/O. It also selects and trusts the evaluator callback. Process isolation requires an additional runtime boundary.
- Python may leave plaintext copies in memory, swap, core dumps or diagnostics. A memory-only threat model needs operating-system controls, callback review and retention testing.
- A remote model receives plaintext. Choose a provider and retention policy approved for that dataset and recipient.
- Existing campaign journals may retain plaintext. A metadata-only protocol needs its own reviewed logging path.
- Existing private plaintext archives remain in place. Production key management and deployment of a protected runtime are continuing work.
- Legal claims and original quality ratings require independent assessment alongside exact-text verification.

The tests verify exact-byte round trips, fresh ciphertext, authentication failure for wrong keys or tampering, and rejection of textual receipts. Secure-enclave isolation and provider-retention guarantees require separate evidence from those systems.
