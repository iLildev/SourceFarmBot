"""
Token encryption/decryption using Fernet symmetric encryption.
The key is stored in the FERNET_KEY environment variable.
On first run, a key is auto-generated and printed — save it to secrets.
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
        key = Fernet.generate_key().decode()
        logger.warning(
            "FERNET_KEY not set — generated ephemeral key (tokens lost on restart!). "
            "Set FERNET_KEY=%s in secrets.", key
        )
    _fernet = Fernet(key.encode() if isinstance(key, str) else key)
    return _fernet


def encrypt_token(token: str) -> str:
    return _get_fernet().encrypt(token.encode()).decode()


def decrypt_token(encrypted: str) -> str:
    return _get_fernet().decrypt(encrypted.encode()).decode()
