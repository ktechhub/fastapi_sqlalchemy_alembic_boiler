"""
Encryption utilities for securing sensitive data in Redis.
Uses Fernet (symmetric encryption) for efficient and secure encryption.
"""

from cryptography.fernet import Fernet
from typing import Optional
import base64
import hashlib
from ..core.config import settings
from ..core.loggers import app_logger as logger

# Cache the Fernet instance for performance
_fernet_instance: Optional[Fernet] = None


def _get_fernet() -> Fernet:
    """Get or create Fernet encryption instance."""
    global _fernet_instance
    if _fernet_instance is None:
        # Generate key from JWT_SECRET_KEY for consistency
        # This ensures we have a 32-byte key for Fernet
        secret_key = settings.JWT_SECRET_KEY.encode()
        # Use SHA256 to get a 32-byte key, then base64 encode for Fernet
        key = base64.urlsafe_b64encode(hashlib.sha256(secret_key).digest())
        _fernet_instance = Fernet(key)
    return _fernet_instance


def hash_token(token: str) -> str:
    """
    Hash a JWT token to create a secure Redis key.
    Uses SHA256 for one-way hashing - token cannot be recovered from hash.

    Args:
        token: JWT token string

    Returns:
        SHA256 hash of the token (hex string)
    """
    return hashlib.sha256(token.encode()).hexdigest()


def encrypt_data(data: str) -> str:
    """
    Encrypt sensitive data before storing in Redis.

    Args:
        data: String data to encrypt

    Returns:
        Encrypted string (base64 encoded)
    """
    try:
        fernet = _get_fernet()
        encrypted = fernet.encrypt(data.encode())
        return encrypted.decode()
    except Exception as e:
        logger.error(f"Error encrypting data: {e}")
        raise


def decrypt_data(encrypted_data: str) -> str:
    """
    Decrypt sensitive data retrieved from Redis.

    Args:
        encrypted_data: Encrypted string (base64 encoded)

    Returns:
        Decrypted string
    """
    try:
        fernet = _get_fernet()
        decrypted = fernet.decrypt(encrypted_data.encode())
        return decrypted.decode()
    except Exception as e:
        logger.error(f"Error decrypting data: {e}")
        raise
