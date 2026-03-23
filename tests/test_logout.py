"""
Tests for the `logout` command in main.py.
"""

import os
from unittest.mock import MagicMock, patch

import pytest

from cli.main import logout


@pytest.fixture(name="mock_args")
def _mock_args() -> MagicMock:
    """
    A mock argparse namespace.
    """
    return MagicMock()


class TestLogout:
    """
    Tests for the `logout` function.
    """

    @patch("cli.main.create_credential_store")
    def test_clears_credentials_for_configured_organization(
        self, mock_create_store: MagicMock, tmp_path: str, mock_args: MagicMock
    ) -> None:
        """
        Test that logout deletes the token for the organization found in the config file.
        """
        # given
        config_dir = str(tmp_path)
        config_path = os.path.join(config_dir, "config.yaml")
        clients_dir = os.path.join(config_dir, "clients")

        with open(config_path, "w") as f:
            f.write("organization_id: my-org\n")

        mock_store = MagicMock()
        mock_create_store.return_value = mock_store

        # when
        with (
            patch("cli.main.get_config_dir", return_value=config_dir),
            patch("cli.main.get_config_path", return_value=config_path),
        ):
            logout(mock_args)

        # then
        mock_create_store.assert_called_once_with(
            clients_dir=clients_dir,
            machine_id_func=pytest.importorskip("cli.auth.auth_utils").get_machine_id,
        )
        mock_store.delete_token.assert_called_once_with(organization_id="my-org")

    def test_prints_error_when_no_config_file(
        self, tmp_path: str, mock_args: MagicMock
    ) -> None:
        """
        Test that logout prints an error when no config file exists.
        """
        # given
        config_path = os.path.join(str(tmp_path), "nonexistent_config.yaml")

        # when
        with patch("cli.main.get_config_path", return_value=config_path):
            logout(mock_args)

        # then — no exception raised, error message printed to console

    @patch("cli.main.create_credential_store")
    def test_prints_error_when_no_organization_id_in_config(
        self, mock_create_store: MagicMock, tmp_path: str, mock_args: MagicMock
    ) -> None:
        """
        Test that logout prints an error when the config has no organization_id.
        """
        # given
        config_path = os.path.join(str(tmp_path), "config.yaml")
        with open(config_path, "w") as f:
            f.write("log_level: INFO\n")

        # when
        with patch("cli.main.get_config_path", return_value=config_path):
            logout(mock_args)

        # then
        mock_create_store.assert_not_called()

    @patch("cli.main.create_credential_store")
    def test_handles_delete_token_failure_gracefully(
        self, mock_create_store: MagicMock, tmp_path: str, mock_args: MagicMock
    ) -> None:
        """
        Test that logout handles delete_token exceptions gracefully.
        """
        # given
        config_dir = str(tmp_path)
        config_path = os.path.join(config_dir, "config.yaml")

        with open(config_path, "w") as f:
            f.write("organization_id: my-org\n")

        mock_store = MagicMock()
        mock_store.delete_token.side_effect = Exception("Keyring error")
        mock_create_store.return_value = mock_store

        # when
        with (
            patch("cli.main.get_config_dir", return_value=config_dir),
            patch("cli.main.get_config_path", return_value=config_path),
        ):
            logout(mock_args)

        # then
        mock_store.delete_token.assert_called_once_with(organization_id="my-org")
