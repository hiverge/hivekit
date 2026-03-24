"""
Tests for the credential store implementations in the auth module.
"""

import os
from unittest.mock import ANY, MagicMock, patch

import pytest

from cli.auth.credential_store import (
    FileCredentialStore,
    KeyringCredentialStore,
    TokenEncryptor,
    create_credential_store,
)

_TEST_MACHINE_ID = "test-machine-id-123"


@pytest.fixture(name="sample_token")
def _sample_token() -> dict:
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


class TestTokenEncryptor:
    """
    Tests for the `TokenEncryptor` class.
    """

    def test_encrypt_and_decrypt_round_trip(
        self, encryptor: TokenEncryptor, sample_token: dict
    ) -> None:
        """
        Test that a token can be encrypted and then decrypted back to the original value.
        """
        # when
        encrypted = encryptor.encrypt(token=sample_token)
        decrypted = encryptor.decrypt(data=encrypted)

        # then
        assert decrypted == sample_token

    def test_encrypted_output_is_a_string(
        self, encryptor: TokenEncryptor, sample_token: dict
    ) -> None:
        """
        Test that the encrypt method returns a string.
        """
        # when
        encrypted = encryptor.encrypt(token=sample_token)

        # then
        assert isinstance(encrypted, str)

    def test_encrypted_output_differs_from_plaintext(
        self, encryptor: TokenEncryptor, sample_token: dict
    ) -> None:
        """
        Test that the encrypted output does not contain the plaintext access token.
        """
        # when
        encrypted = encryptor.encrypt(token=sample_token)

        # then
        assert "access-123" not in encrypted


class TestKeyringCredentialStore:
    """
    Tests for the `KeyringCredentialStore` class.
    """

    @pytest.fixture(name="mock_keyring")
    def _mock_keyring(self) -> MagicMock:
        """
        A mock keyring backend.
        """
        return MagicMock()

    def test_save_token(
        self,
        mock_keyring: MagicMock,
        encryptor: TokenEncryptor,
        sample_token: dict,
    ) -> None:
        """
        Test that saving a token calls keyring.set_password with an encrypted value.
        """
        # given
        store = KeyringCredentialStore(keyring_backend=mock_keyring, encryptor=encryptor)

        # when
        store.save_token(organization_id="my-org", token=sample_token)

        # then
        mock_keyring.set_password.assert_called_once_with("hivekit", "my-org", ANY)
        encrypted_value = mock_keyring.set_password.call_args[0][2]
        assert encryptor.decrypt(data=encrypted_value) == sample_token

    def test_load_token(
        self,
        mock_keyring: MagicMock,
        encryptor: TokenEncryptor,
        sample_token: dict,
    ) -> None:
        """
        Test that loading a token calls keyring.get_password and decrypts the result.
        """
        # given
        encrypted_value = encryptor.encrypt(token=sample_token)
        mock_keyring.get_password.return_value = encrypted_value
        store = KeyringCredentialStore(keyring_backend=mock_keyring, encryptor=encryptor)

        # when
        result = store.load_token(organization_id="my-org")

        # then
        assert result == sample_token
        mock_keyring.get_password.assert_called_once_with("hivekit", "my-org")

    def test_load_token_returns_none_when_not_found(
        self, mock_keyring: MagicMock, encryptor: TokenEncryptor
    ) -> None:
        """
        Test that loading a token returns None when the keyring has no stored value.
        """
        # given
        mock_keyring.get_password.return_value = None
        store = KeyringCredentialStore(keyring_backend=mock_keyring, encryptor=encryptor)

        # when
        result = store.load_token(organization_id="my-org")

        # then
        assert result is None
        mock_keyring.get_password.assert_called_once_with("hivekit", "my-org")

    def test_delete_token(
        self, mock_keyring: MagicMock, encryptor: TokenEncryptor
    ) -> None:
        """
        Test that deleting a token calls keyring.delete_password with the correct arguments.
        """
        # given
        store = KeyringCredentialStore(keyring_backend=mock_keyring, encryptor=encryptor)

        # when
        store.delete_token(organization_id="my-org")

        # then
        mock_keyring.delete_password.assert_called_once_with("hivekit", "my-org")

    def test_save_and_load_round_trip(
        self,
        mock_keyring: MagicMock,
        encryptor: TokenEncryptor,
        sample_token: dict,
    ) -> None:
        """
        Test that a token saved to the keyring can be loaded back correctly.
        """
        # given
        stored_data = {}
        mock_keyring.set_password.side_effect = (
            lambda service, username, password: stored_data.update({(service, username): password})
        )
        mock_keyring.get_password.side_effect = lambda service, username: stored_data.get(
            (service, username)
        )
        store = KeyringCredentialStore(keyring_backend=mock_keyring, encryptor=encryptor)

        # when
        store.save_token(organization_id="my-org", token=sample_token)
        result = store.load_token(organization_id="my-org")

        # then
        assert result == sample_token


class TestFileCredentialStore:
    """
    Tests for the `FileCredentialStore` class.
    """

    def test_save_and_load_token(
        self, tmp_path: str, encryptor: TokenEncryptor, sample_token: dict
    ) -> None:
        """
        Test that a token can be saved and then loaded back correctly.
        """
        # given
        store = FileCredentialStore(clients_dir=str(tmp_path), encryptor=encryptor)

        # when
        store.save_token(organization_id="my-org", token=sample_token)
        result = store.load_token(organization_id="my-org")

        # then
        assert result == sample_token

    def test_load_token_returns_none_when_file_missing(
        self, tmp_path: str, encryptor: TokenEncryptor
    ) -> None:
        """
        Test that loading a token returns None when no credential file exists.
        """
        # given
        store = FileCredentialStore(clients_dir=str(tmp_path), encryptor=encryptor)

        # when
        result = store.load_token(organization_id="nonexistent-org")

        # then
        assert result is None

    def test_delete_token(
        self, tmp_path: str, encryptor: TokenEncryptor, sample_token: dict
    ) -> None:
        """
        Test that deleting a token removes the credential file.
        """
        # given
        store = FileCredentialStore(clients_dir=str(tmp_path), encryptor=encryptor)
        store.save_token(organization_id="my-org", token=sample_token)

        # when
        store.delete_token(organization_id="my-org")

        # then
        result = store.load_token(organization_id="my-org")
        assert result is None

    def test_delete_token_when_file_missing(
        self, tmp_path: str, encryptor: TokenEncryptor
    ) -> None:
        """
        Test that deleting a token when no file exists does not raise an error.
        """
        # given
        store = FileCredentialStore(clients_dir=str(tmp_path), encryptor=encryptor)

        # when / then — should not raise
        store.delete_token(organization_id="nonexistent-org")

    def test_token_file_is_created_in_correct_location(
        self, tmp_path: str, encryptor: TokenEncryptor, sample_token: dict
    ) -> None:
        """
        Test that the credential file is created at the expected path.
        """
        # given
        store = FileCredentialStore(clients_dir=str(tmp_path), encryptor=encryptor)

        # when
        store.save_token(organization_id="my-org", token=sample_token)

        # then
        expected_path = os.path.join(str(tmp_path), "my-org_client")
        assert os.path.exists(expected_path)

    def test_stored_file_is_encrypted(
        self, tmp_path: str, encryptor: TokenEncryptor, sample_token: dict
    ) -> None:
        """
        Test that the credential file content does not contain the plaintext access token.
        """
        # given
        store = FileCredentialStore(clients_dir=str(tmp_path), encryptor=encryptor)

        # when
        store.save_token(organization_id="my-org", token=sample_token)

        # then
        path = os.path.join(str(tmp_path), "my-org_client")
        with open(path, "r") as f:
            content = f.read()
        assert "access-123" not in content


class TestCreateCredentialStore:
    """
    Tests for the `create_credential_store` factory function.
    """

    @patch("cli.auth.credential_store.keyring")
    def test_returns_keyring_store_when_available(self, mock_keyring: MagicMock) -> None:
        """
        Test that the factory returns a KeyringCredentialStore when keyring is available.
        """
        # given
        mock_backend = MagicMock()
        mock_backend.priority.return_value = 5
        mock_backend.get_password.return_value = None
        mock_keyring.get_keyring.return_value = mock_backend

        # when
        store = create_credential_store(
            clients_dir="/tmp/test",
            machine_id_func=lambda: "test-id",
        )

        # then
        assert isinstance(store, KeyringCredentialStore)
        mock_backend.get_password.assert_called_once_with("hivekit", "_probe")

    @patch("cli.auth.credential_store.keyring")
    def test_returns_file_store_when_keyring_unavailable(
        self, mock_keyring: MagicMock
    ) -> None:
        """
        Test that the factory falls back to FileCredentialStore when keyring raises an exception.
        """
        # given
        mock_backend = MagicMock()
        mock_backend.priority.return_value = 5
        mock_backend.get_password.side_effect = Exception("No keyring backend")
        mock_keyring.get_keyring.return_value = mock_backend

        # when
        store = create_credential_store(
            clients_dir="/tmp/test",
            machine_id_func=lambda: "test-id",
        )

        # then
        assert isinstance(store, FileCredentialStore)
        mock_backend.get_password.assert_called_once_with("hivekit", "_probe")
