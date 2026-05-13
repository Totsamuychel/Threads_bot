"""Symmetric encryption utilities for sensitive fields stored in the database."""

import base64
import hashlib
from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import String
from sqlalchemy.types import TypeDecorator


def _fernet(secret_key: str) -> Fernet:
    key = hashlib.sha256(secret_key.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(key))


def encrypt_value(value: str, secret_key: str) -> str:
    return _fernet(secret_key).encrypt(value.encode()).decode()


def decrypt_value(encrypted: str, secret_key: str) -> str:
    return _fernet(secret_key).decrypt(encrypted.encode()).decode()


class EncryptedString(TypeDecorator):
    """Column type that transparently encrypts/decrypts using settings.secret_key."""

    impl = String
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        from app.config import settings
        return encrypt_value(value, settings.secret_key)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        from app.config import settings
        try:
            return decrypt_value(value, settings.secret_key)
        except (InvalidToken, Exception):
            return value
