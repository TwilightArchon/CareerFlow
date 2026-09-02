from __future__ import annotations

import base64
import json
import os
from dataclasses import dataclass
from typing import Any

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


@dataclass(frozen=True)
class EncryptedPayload:
    version: int
    nonce: str
    ciphertext: str

    def encode(self) -> str:
        return json.dumps(
            {"version": self.version, "nonce": self.nonce, "ciphertext": self.ciphertext},
            separators=(",", ":"),
        )

    @classmethod
    def decode(cls, value: str) -> EncryptedPayload:
        parsed = json.loads(value)
        return cls(
            version=int(parsed["version"]),
            nonce=str(parsed["nonce"]),
            ciphertext=str(parsed["ciphertext"]),
        )


class PayloadCipher:
    """AES-256-GCM envelope encryption. The caller obtains the key from macOS Keychain."""

    def __init__(self, key: bytes) -> None:
        if len(key) != 32:
            raise ValueError("AES-256-GCM requires a 32-byte key")
        self._aes = AESGCM(key)

    @staticmethod
    def new_key() -> bytes:
        return AESGCM.generate_key(bit_length=256)

    def encrypt(self, value: bytes, *, associated_data: bytes) -> str:
        nonce = os.urandom(12)
        encrypted = self._aes.encrypt(nonce, value, associated_data)
        return EncryptedPayload(
            version=1,
            nonce=base64.b64encode(nonce).decode("ascii"),
            ciphertext=base64.b64encode(encrypted).decode("ascii"),
        ).encode()

    def decrypt(self, value: str, *, associated_data: bytes) -> bytes:
        payload = EncryptedPayload.decode(value)
        if payload.version != 1:
            raise ValueError("Unsupported encrypted payload version")
        return self._aes.decrypt(
            base64.b64decode(payload.nonce),
            base64.b64decode(payload.ciphertext),
            associated_data,
        )


REDACTED = "[REDACTED]"
SECRET_KEYS = frozenset(
    {
        "authorization",
        "api_key",
        "access_token",
        "refresh_token",
        "password",
        "captcha",
        "two_factor_code",
        "otp",
    }
)


def redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: REDACTED if key.lower() in SECRET_KEYS else redact(child)
            for key, child in value.items()
        }
    if isinstance(value, list):
        return [redact(child) for child in value]
    if isinstance(value, tuple):
        return tuple(redact(child) for child in value)
    return value
