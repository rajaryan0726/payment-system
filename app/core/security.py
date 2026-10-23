import hashlib
import hmac
import secrets
from typing import Tuple
import bcrypt


def generate_client_credentials(is_test: bool = True) -> Tuple[str, str, str]:
    """
    Generates a secure key_id, plaintext client_secret, and its bcrypt secret_hash.
    Returns: (key_id, plaintext_secret, secret_hash)
    Note: Plaintext secret is returned ONLY once for initial display to the client.
    """
    prefix = "key_test_" if is_test else "key_live_"
    key_id = f"{prefix}{secrets.token_hex(12)}"
    plaintext_secret = f"sec_{secrets.token_urlsafe(32)}"

    secret_hash = bcrypt.hashpw(plaintext_secret.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    return key_id, plaintext_secret, secret_hash


def verify_client_secret(plaintext_secret: str, secret_hash: str) -> bool:
    """Verifies a plaintext secret against its stored bcrypt hash in constant time."""
    try:
        return bcrypt.checkpw(plaintext_secret.encode("utf-8"), secret_hash.encode("utf-8"))
    except Exception:
        return False


def verify_hmac_sha256(data: bytes, secret: str, expected_signature: str) -> bool:
    """Verifies an HMAC SHA-256 signature using constant-time comparison."""
    if not secret or not expected_signature:
        return False
    computed = hmac.new(secret.encode("utf-8"), data, hashlib.sha256).hexdigest()
    return hmac.compare_digest(computed.lower(), expected_signature.lower())
