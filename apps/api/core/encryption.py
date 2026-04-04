"""Fernet symmetric encryption for token storage."""

import os

from cryptography.fernet import Fernet

ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", Fernet.generate_key().decode())

_fernet = Fernet(ENCRYPTION_KEY.encode() if isinstance(ENCRYPTION_KEY, str) else ENCRYPTION_KEY)


def encrypt_token(plaintext: str) -> str:
    """Encrypt a token string using Fernet."""
    return _fernet.encrypt(plaintext.encode()).decode()


def decrypt_token(ciphertext: str) -> str:
    """Decrypt a Fernet-encrypted token string."""
    return _fernet.decrypt(ciphertext.encode()).decode()
