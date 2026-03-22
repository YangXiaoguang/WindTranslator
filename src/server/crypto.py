"""Fernet-based symmetric encryption for API keys."""

from __future__ import annotations

import logging

from cryptography.fernet import Fernet, InvalidToken

from .config import get_settings

log = logging.getLogger(__name__)


def _get_fernet() -> Fernet:
    """Build a Fernet instance from the configured encryption key."""
    key = get_settings().encryption_key
    if not key:
        raise RuntimeError(
            "WT_ENCRYPTION_KEY 未设置。"
            "请运行 python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())' "
            "生成密钥并设置环境变量。"
        )
    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt_api_key(plain_key: str) -> str:
    """Encrypt an API key for database storage."""
    return _get_fernet().encrypt(plain_key.encode()).decode()


def decrypt_api_key(encrypted_key: str) -> str:
    """Decrypt an API key read from the database."""
    try:
        return _get_fernet().decrypt(encrypted_key.encode()).decode()
    except InvalidToken as exc:
        raise ValueError("API Key 解密失败，请检查 WT_ENCRYPTION_KEY 是否正确") from exc
