"""
Integration tests for the `KeyringCredentialStore` using a real keyring backend.
"""

from typing import Dict, Generator

import keyring as real_keyring
import pytest

from cli.auth.credential_store import KeyringCredentialStore, TokenEncryptor

_TEST_MACHINE_ID = "test-machine-id-123"
_SERVICE = "hivekit"
_ORG_ID = "integration-test-org"


@pytest.fixture(name="sample_token")
def _sample_token() -> Dict[str, object]:
    """
    A sample OAuth token dict for testing.
    """
    return {
        "access_token": "access-123",
        "refresh_token": "refresh-456",
        "token_type": "Bearer",
        "expires_in": 300,
    }


@pytest.fixture(name="encryptor")
def _encryptor() -> TokenEncryptor:
    """
    A token encryptor using a fixed test machine ID.
    """
    return TokenEncryptor(machine_id=_TEST_MACHINE_ID)


@pytest.fixture(name="keyring_store")
def _keyring_store(encryptor: TokenEncryptor) -> Generator[KeyringCredentialStore, None, None]:
    """
    A KeyringCredentialStore backed by the real system keyring.
    Cleans up any stored tokens after the test.
    """
    backend = real_keyring.get_keyring()
    store = KeyringCredentialStore(keyring_backend=backend, encryptor=encryptor)
    yield store
    # Cleanup: remove the test entry from the keyring
    try:
        backend.delete_password(_SERVICE, _ORG_ID)
    except Exception:
        pass


@pytest.mark.integration
class TestKeyringCredentialStoreIntegration:
    """
    Integration tests for the `KeyringCredentialStore` using a real keyring backend.
    """

    def test_save_and_load_round_trip(
        self,
        keyring_store: KeyringCredentialStore,
        sample_token: dict,
    ) -> None:
        """
        Test that a token can be saved to and loaded from the real system keyring.
        """
        # when
        keyring_store.save_token(organization_id=_ORG_ID, token=sample_token)
        result = keyring_store.load_token(organization_id=_ORG_ID)

        # then
        assert result == sample_token

    def test_delete_token(
        self,
        keyring_store: KeyringCredentialStore,
        sample_token: dict,
    ) -> None:
        """
        Test that a token can be deleted from the real system keyring.
        """
        # given
        keyring_store.save_token(organization_id=_ORG_ID, token=sample_token)

        # when
        keyring_store.delete_token(organization_id=_ORG_ID)
        result = keyring_store.load_token(organization_id=_ORG_ID)

        # then
        assert result is None

    def test_load_returns_none_when_no_entry_exists(
        self,
        keyring_store: KeyringCredentialStore,
    ) -> None:
        """
        Test that loading a non-existent token from the real keyring returns None.
        """
        # when
        result = keyring_store.load_token(organization_id=_ORG_ID)

        # then
        assert result is None
