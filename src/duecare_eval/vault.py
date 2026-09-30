"""Optional authenticated storage and local, text-free comparison receipts.

No disk or network I/O occurs here. This is NOT a memory-isolation sandbox:
the caller/evaluator and OS must enforce their own logging, swap and dump policy.
"""
import hashlib
import hmac
import math
import os

MAGIC = b"DUECARE-AESGCM-1\x00"
METRICS = {"items", "accuracy", "matches", "errors", "mean_score", "duration_seconds"}


def seal(plaintext: bytes, key: bytes) -> bytes:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    if len(key) != 32 or not isinstance(plaintext, bytes):
        raise ValueError("require_256_bit_key_and_bytes")
    nonce = os.urandom(12)
    return MAGIC + nonce + AESGCM(key).encrypt(nonce, plaintext, MAGIC)


def open_in_memory(envelope: bytes, key: bytes) -> bytes:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    if len(key) != 32 or not envelope.startswith(MAGIC) or len(envelope) < len(MAGIC)+28:
        raise ValueError("invalid_vault_envelope")
    pos = len(MAGIC)
    return AESGCM(key).decrypt(envelope[pos:pos+12], envelope[pos+12:], MAGIC)


def compare_locally(envelope: bytes, key: bytes, evaluator) -> dict:
    """Pass exact bytes to a trusted local evaluator; return fixed numeric fields.

    The callback is trusted code, not confined by this function. Do not pass a
    provider adapter or a callback that persists prompts/responses.
    """
    plaintext = open_in_memory(envelope, key)
    metrics = evaluator(plaintext)
    if not isinstance(metrics, dict) or not set(metrics) <= METRICS:
        raise ValueError("numeric_metrics_only")
    if any(type(v) not in (int, float, bool) or not math.isfinite(v) for v in metrics.values()):
        raise ValueError("finite_numeric_metrics_only")
    receipt_key = hmac.digest(key, b"duecare-vault-receipt-key", "sha256")
    return {"protocol":"duecare-local-full-text-comparison/1.0.0", "metrics":metrics,
            "source_hmac":hmac.new(receipt_key, plaintext, hashlib.sha256).hexdigest(),
            "plaintext_in_receipt":False}
