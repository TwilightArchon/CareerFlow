from __future__ import annotations

import keyring

SERVICE_NAME = "dev.careerflow.desktop"


class KeychainUnavailableError(RuntimeError):
    pass


class KeychainSecretStore:
    """Narrow wrapper around macOS Keychain. Callers persist only returned references."""

    def put(self, reference: str, value: str) -> None:
        try:
            keyring.set_password(SERVICE_NAME, reference, value)
        except keyring.errors.KeyringError as error:
            raise KeychainUnavailableError("macOS Keychain is unavailable") from error

    def get(self, reference: str) -> str | None:
        try:
            return keyring.get_password(SERVICE_NAME, reference)
        except keyring.errors.KeyringError as error:
            raise KeychainUnavailableError("macOS Keychain is unavailable") from error

    def delete(self, reference: str) -> None:
        try:
            keyring.delete_password(SERVICE_NAME, reference)
        except keyring.errors.PasswordDeleteError:
            return
        except keyring.errors.KeyringError as error:
            raise KeychainUnavailableError("macOS Keychain is unavailable") from error
