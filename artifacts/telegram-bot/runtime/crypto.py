"""
Token encryption/decryption using Fernet symmetric encryption.
FERNET_KEY must be set in secrets — never leave it unset in production.
Generate one: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
"""
import os
import logging
from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)

_fernet: Fernet | None = None


def _get_fernet() -> Fernet:
    global _fernet
    if _fernet is not None:
        return _fernet

    key = os.environ.get("FERNET_KEY", "").strip()
    if not key:
        raise RuntimeError(
            "FERNET_KEY is not set. "
            "Generate one with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\" "
            "then add it to your Replit secrets. Without it, bot tokens cannot be encrypted and the platform cannot start."
        )

    try:
        _fernet = Fernet(key.encode())
    except Exception as exc:
        raise RuntimeError(f"FERNET_KEY is invalid: {exc}") from exc

    logger.info("Fernet encryption initialised.")
    return _fernet


def encrypt_token(token: str) -> str:
    return _get_fernet().encrypt(token.encode()).decode()


def decrypt_token(encrypted: str) -> str:
    return _get_fernet().decrypt(encrypted.encode()).decode()
