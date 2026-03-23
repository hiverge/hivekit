"""
Tests for the `logout` command in main.py.
"""

import os
from unittest.mock import MagicMock, call, patch

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
        os.makedirs(clients_dir)

        with open(config_path, "w") as f:
            f.write("organization_id: my-org\n")

        mock_store = MagicMock()
        mock_create_store.return_value = mock_store

        # when
        with patch("cli.main._CONFIG_DIR", config_dir), patch("cli.main._CONFIG_PATH", config_path):
            logout(mock_args)

        # then
        mock_create_store.assert_called_once_with(
            clients_dir=clients_dir,
            machine_id_func=pytest.importorskip("cli.utils.machine_id").get_machine_id,
        )
        mock_store.delete_token.assert_called_once_with(organization_id="my-org")

    @patch("cli.main.create_credential_store")
    def test_clears_file_based_credentials_from_clients_directory(
        self, mock_create_store: MagicMock, tmp_path: str, mock_args: MagicMock
    ) -> None:
        """
        Test that logout also scans the clients directory and removes credentials
        for organizations not in the config.
        """
        # given
        config_dir = str(tmp_path)
        config_path = os.path.join(config_dir, "config.yaml")
        clients_dir = os.path.join(config_dir, "clients")
        os.makedirs(clients_dir)

        with open(config_path, "w") as f:
            f.write("organization_id: org-a\n")

        # Create credential files for two orgs
        with open(os.path.join(clients_dir, "org-a_client"), "w") as f:
            f.write("encrypted-token")
        with open(os.path.join(clients_dir, "org-b_client"), "w") as f:
            f.write("encrypted-token")

        mock_store = MagicMock()
        mock_create_store.return_value = mock_store

        # when
        with patch("cli.main._CONFIG_DIR", config_dir), patch("cli.main._CONFIG_PATH", config_path):
            logout(mock_args)

        # then
        mock_store.delete_token.assert_has_calls(
            [call(organization_id="org-a"), call(organization_id="org-b")],
            any_order=True,
        )
        assert mock_store.delete_token.call_count == 2

    @patch("cli.main.create_credential_store")
    def test_prints_message_when_no_credentials_found(
        self, mock_create_store: MagicMock, tmp_path: str, mock_args: MagicMock
    ) -> None:
        """
        Test that logout prints a message when there are no stored credentials.
        """
        # given
        config_dir = str(tmp_path)
        config_path = os.path.join(config_dir, "nonexistent_config.yaml")

        mock_store = MagicMock()
        mock_create_store.return_value = mock_store

        # when
        with patch("cli.main._CONFIG_DIR", config_dir), patch("cli.main._CONFIG_PATH", config_path):
            logout(mock_args)

        # then
        mock_store.delete_token.assert_not_called()
