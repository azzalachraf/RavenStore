from __future__ import annotations

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings


class SecretCipher:
    def __init__(self, key: str):
        self._fernet = Fernet(key.encode())

    def encrypt(self, value: str) -> str:
        return self._fernet.encrypt(value.encode()).decode()

    def decrypt(self, value: str) -> str:
        try:
            return self._fernet.decrypt(value.encode()).decode()
        except InvalidToken as exc:
            raise ValueError("security.decrypt_failed") from exc


cipher = SecretCipher(settings.encryption_key)

