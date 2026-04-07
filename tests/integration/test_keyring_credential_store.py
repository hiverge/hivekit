"""
Integration tests for the `KeyringCredentialStore` using a real keyring backend.
"""

from typing import Dict, Generator

import keyring as real_keyring
import pytest

from cli.auth.credential_store import (
    CredentialStore,
    KeyringCredentialStore,
    create_credential_store,
)

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


@pytest.fixture(name="credential_store")
def _credential_store(tmp_path: str) -> Generator[CredentialStore, None, None]:
    """
    A credential store created via the factory function.
    Cleans up any stored tokens after the test.
    """
    store = create_credential_store(
        clients_dir=str(tmp_path),
        machine_id_func=lambda: _TEST_MACHINE_ID,
    )
    yield store
    # Cleanup: remove the test entry from the keyring if it was a keyring store
    if isinstance(store, KeyringCredentialStore):
        try:
            real_keyring.get_keyring().delete_password(_SERVICE, _ORG_ID)
        except Exception:
            pass


@pytest.mark.integration
class TestKeyringCredentialStoreIntegration:
    """
    Integration tests for the `KeyringCredentialStore` using a real keyring backend.
    """

    def test_factory_returns_keyring_store(
        self,
        credential_store: CredentialStore,
    ) -> None:
        """
        Test that create_credential_store returns a KeyringCredentialStore
        when a real keyring backend is available.
        """
        # then
        assert isinstance(credential_store, KeyringCredentialStore)

    def test_save_and_load_round_trip(
        self,
        credential_store: CredentialStore,
        sample_token: dict,
    ) -> None:
        """
        Test that a token can be saved to and loaded from the real system keyring.
        """
        # when
        credential_store.save_token(organization_id=_ORG_ID, token=sample_token)
        result = credential_store.load_token(organization_id=_ORG_ID)

        # then
        assert result == sample_token

    def test_delete_token(
        self,
        credential_store: CredentialStore,
        sample_token: dict,
    ) -> None:
        """
        Test that a token can be deleted from the real system keyring.
        """
        # given
        credential_store.save_token(organization_id=_ORG_ID, token=sample_token)

        # when
        credential_store.delete_token(organization_id=_ORG_ID)
        result = credential_store.load_token(organization_id=_ORG_ID)

        # then
        assert result is None

    def test_load_returns_none_when_no_entry_exists(
        self,
        credential_store: CredentialStore,
    ) -> None:
        """
        Test that loading a non-existent token from the real keyring returns None.
        """
        # when
        result = credential_store.load_token(organization_id=_ORG_ID)

        # then
        assert result is None
