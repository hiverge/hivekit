"""
Credential storage for OIDC tokens, with keyring and file-based backends.

The `create_credential_store` factory function should
be used to obtain a store instance: it probes the system keyring and falls
back to file-based storage if the keyring is unavailable.
"""

import base64
import hashlib
import json
import logging
import os
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, Optional

import keyring
from cryptography.fernet import Fernet

_KEYRING_SERVICE = "hivekit"

logger = logging.getLogger(_KEYRING_SERVICE)


class TokenEncryptor:
    """
    Encrypts and decrypts token payloads using Fernet with a key derived from the machine ID.

    **Note**: this is not a strong security control since the machine ID is obtainable by any
    process on the same host, but it prevents casual inspection of stored credentials. It also
    *possibly* helps with certain scenarios, like a user syncing their files to an insecure
    location.
    """

    def __init__(self, machine_id: str) -> None:
        """
        Initialize the encryptor.

        Args:
            machine_id: A machine-specific identifier used to derive the encryption key.
        """
        key = base64.urlsafe_b64encode(hashlib.sha256(machine_id.encode()).digest())
        self._fernet = Fernet(key)

    def encrypt(self, token: Dict[str, Any]) -> str:
        """
        Serialize and encrypt a token dict, returning a UTF-8 string.
        """
        return self._fernet.encrypt(json.dumps(token).encode()).decode()

    def decrypt(self, data: str) -> Dict[str, Any]:
        """
        Decrypt and deserialize an encrypted token string back to a dict.
        """
        return json.loads(self._fernet.decrypt(data.encode()))


class CredentialStore(ABC):
    """
    Abstract base class for credential storage backends.
    """

    @abstractmethod
    def save_token(self, organization_id: str, token: Dict[str, Any]) -> None:
        """
        Persist an OAuth token for the given organization.
        """

    @abstractmethod
    def load_token(self, organization_id: str) -> Optional[Dict[str, Any]]:
        """
        Load a previously stored OAuth token for the given organization.

        Returns None if no token is stored.
        """

    @abstractmethod
    def delete_token(self, organization_id: str) -> None:
        """
        Delete a stored OAuth token for the given organization.
        """


class KeyringCredentialStore(CredentialStore):
    """
    Credential store backed by the system keyring (e.g. macOS Keychain).
    """

    def __init__(self, keyring_backend: Any, encryptor: TokenEncryptor) -> None:
        """
        Initialize the keyring credential store.

        Args:
            keyring_backend: The keyring module or compatible object providing
                get_password, set_password, and delete_password methods.
            encryptor: The token encryptor for encrypting/decrypting tokens.
        """
        self._keyring = keyring_backend
        self._encryptor = encryptor

    def save_token(self, organization_id: str, token: Dict[str, Any]) -> None:
        """
        Encrypt and save an OAuth token to the system keyring.
        """
        encrypted = self._encryptor.encrypt(token=token)
        self._keyring.set_password(_KEYRING_SERVICE, organization_id, encrypted)

    def load_token(self, organization_id: str) -> Optional[Dict[str, Any]]:
        """
        Load and decrypt an OAuth token from the system keyring.
        """
        raw = self._keyring.get_password(_KEYRING_SERVICE, organization_id)
        if raw is None:
            logger.info(f"No stored token found in keyring for organization '{organization_id}'.")
            return None
        try:
            return self._encryptor.decrypt(data=raw)
        except Exception:
            logger.warning(
                f"Failed to read stored token from keyring for organization '{organization_id}'. "
                "The token may be corrupted or the machine ID may have changed.", exc_info=True
            )
            return None

    def delete_token(self, organization_id: str) -> None:
        """
        Delete an OAuth token from the system keyring.
        """
        self._keyring.delete_password(_KEYRING_SERVICE, organization_id)


class FileCredentialStore(CredentialStore):
    """
    Credential store backed by files on disk.

    This should *not* be used except as a backup if `KeyringCredentialStore` is not available.
    Although files are encrypted, the encryption key is the machine ID so this is not secure.
    """

    def __init__(self, clients_dir: str, encryptor: TokenEncryptor) -> None:
        """
        Initialize the file-based credential store.

        Args:
            clients_dir: Directory where credential files are stored.
            encryptor: The token encryptor for encrypting/decrypting tokens.
        """
        self._clients_dir = clients_dir
        self._encryptor = encryptor

    def save_token(self, organization_id: str, token: Dict[str, Any]) -> None:
        """
        Encrypt and save an OAuth token to a file.
        """
        os.makedirs(self._clients_dir, exist_ok=True)
        path = self._token_path(organization_id=organization_id)
        encrypted = self._encryptor.encrypt(token=token)
        with open(path, "w") as f:
            f.write(encrypted)

    def load_token(self, organization_id: str) -> Optional[Dict[str, Any]]:
        """
        Load and decrypt an OAuth token from a file.
        """
        path = self._token_path(organization_id=organization_id)
        if not os.path.exists(path):
            logger.info(f"No stored token file found for organization '{organization_id}' at {path}.")
            return None
        try:
            with open(path, "r") as f:
                encrypted = f.read()
            return self._encryptor.decrypt(data=encrypted)
        except Exception:
            logger.warning(
                f"Failed to read stored token for organization '{organization_id}' from {path}. "
                "The token may be corrupted or the machine ID may have changed.", exc_info=True
            )
            return None

    def delete_token(self, organization_id: str) -> None:
        """
        Delete a stored credential file.
        """
        path = self._token_path(organization_id=organization_id)
        if os.path.exists(path):
            os.remove(path)

    def _token_path(self, organization_id: str) -> str:
        """
        Return the file path for the given organization's credential file.
        """
        return os.path.join(self._clients_dir, f"{organization_id}_client")


def create_credential_store(
    clients_dir: str, machine_id_func: Callable[[], str]
) -> CredentialStore:
    """
    Create a credential store, preferring keyring if available.

    Falls back to file-based storage if the system keyring is not usable.
    Both backends encrypt tokens using a Fernet key derived from the machine ID
    (although this is not a strong security control since the machine ID is obtainable by any
    process on the same host)

    Args:
        clients_dir: Directory for file-based credential storage.
        machine_id_func: Callable that returns a machine-specific identifier.
    """
    machine_id = machine_id_func()
    encryptor = TokenEncryptor(machine_id=machine_id)
    try:
        # Probe whether the keyring backend is functional
        keyring_backend = keyring.get_keyring()
        # Keyring comes with some "dummy" backends that have a priority of zero or less.
        if keyring_backend.priority <= 0:
            raise ValueError(f"Keyring backend has a priority of {keyring_backend.priority}")
        keyring_backend.get_password("hivekit", "_probe")
        return KeyringCredentialStore(keyring_backend=keyring_backend, encryptor=encryptor)
    except Exception:
        logger.warning(
            "System keyring is not available. Credentials will be stored in the filesystem."
        )
        return FileCredentialStore(
            clients_dir=clients_dir,
            encryptor=encryptor,
        )
