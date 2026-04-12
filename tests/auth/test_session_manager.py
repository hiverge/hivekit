"""
Tests for the `OidcSessionManager` class and `create_session_manager` factory.
"""

from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture

from cli.auth.credential_store import CredentialStore
from cli.auth.oidc_flow import OidcLoginFlow
from cli.auth.session_manager import (
    OidcSessionManager,
    create_session_manager,
)


@pytest.fixture(name="mock_credential_store")
def _mock_credential_store() -> MagicMock:
    """
    A mock credential store.
    """
    return MagicMock(spec=CredentialStore)


@pytest.fixture(name="mock_login_flow")
def _mock_login_flow() -> MagicMock:
    """
    A mock OIDC login flow.
    """
    return MagicMock(spec=OidcLoginFlow)


@pytest.fixture(name="session_manager")
def _session_manager(
    mock_credential_store: MagicMock,
    mock_login_flow: MagicMock,
) -> OidcSessionManager:
    """
    An OidcSessionManager configured with mock dependencies.
    """
    return OidcSessionManager(
        organization_id="test-org",
        credential_store=mock_credential_store,
        login_flow=mock_login_flow,
        token_endpoint="https://identity.example.com/realms/test-org/protocol/openid-connect/token",
        insecure=False,
    )


class TestOidcSessionManager:
    """
    Tests for the `OidcSessionManager` class and the `create_session_manager` factory.
    """

    def test_create_session_returns_session_from_stored_token(
        self, session_manager: OidcSessionManager,
        mock_credential_store: MagicMock, mock_login_flow: MagicMock,
    ) -> None:
        """
        Test that create_session returns an OAuth2Session from a stored token
        without initiating the login flow.
        """
        # given
        mock_credential_store.load_token.return_value = {
            "access_token": "stored-token",
            "token_type": "Bearer",
        }

        # when
        session = session_manager.create_session()

        # then
        assert session.token == {
            "access_token": "stored-token",
            "token_type": "Bearer",
        }
        mock_credential_store.load_token.assert_called_once_with(organization_id="test-org")
        mock_login_flow.login.assert_not_called()

    def test_create_session_initiates_login_flow_when_no_stored_token(
        self, session_manager: OidcSessionManager,
        mock_credential_store: MagicMock, mock_login_flow: MagicMock,
    ) -> None:
        """
        Test that create_session initiates the login flow when no stored token
        is available.
        """
        # given
        mock_credential_store.load_token.return_value = None
        mock_login_flow.login.return_value = {
            "access_token": "fresh-token",
            "token_type": "Bearer",
        }

        # when
        session = session_manager.create_session()

        # then
        assert session.token == {
            "access_token": "fresh-token",
            "token_type": "Bearer",
        }
        mock_credential_store.load_token.assert_called_once_with(organization_id="test-org")
        mock_login_flow.login.assert_called_once()

    def test_login_runs_flow_and_persists_token(
        self, session_manager: OidcSessionManager,
        mock_credential_store: MagicMock, mock_login_flow: MagicMock,
    ) -> None:
        """
        Test that login runs the OIDC login flow, persists the token, and
        returns an OAuth2Session.
        """
        # given
        mock_login_flow.login.return_value = {
            "access_token": "fresh-token",
            "token_type": "Bearer",
        }

        # when
        session = session_manager.login()

        # then
        assert session.token == {
            "access_token": "fresh-token",
            "token_type": "Bearer",
        }
        mock_login_flow.login.assert_called_once()
        mock_credential_store.save_token.assert_called_once_with(
            organization_id="test-org",
            token={"access_token": "fresh-token", "token_type": "Bearer"},
        )

    def test_create_session_manager_wires_dependencies(
        self, mocker: MockerFixture,
    ) -> None:
        """
        Test that create_session_manager creates a manager with the correct
        token endpoint and wires up all dependencies.
        """
        # given
        mock_derive_url = mocker.patch(
            "cli.auth.session_manager.derive_identity_base_url",
            return_value="https://platform.hiverge.ai/identity",
        )
        mocker.patch("cli.auth.session_manager.get_config_dir", return_value="/home/user/.hive")

        mock_create_store = mocker.patch("cli.auth.session_manager.create_credential_store")
        mock_store = MagicMock(spec=CredentialStore)
        mock_create_store.return_value = mock_store

        mock_login_flow_cls = mocker.patch("cli.auth.session_manager.OidcLoginFlow")
        mock_flow = MagicMock(spec=OidcLoginFlow)
        mock_login_flow_cls.return_value = mock_flow

        # when
        manager = create_session_manager(
            organization_id="my-org",
            base_url="https://platform.hiverge.ai/api/v1",
            insecure=True,
        )

        # then
        mock_derive_url.assert_called_once_with(
            api_endpoint="https://platform.hiverge.ai/api/v1",
        )
        mock_create_store.assert_called_once_with(
            clients_dir="/home/user/.hive/clients",
            machine_id_func=pytest.importorskip("cli.auth.auth_utils").get_machine_id,
        )
        mock_login_flow_cls.assert_called_once_with(
            identity_base_url="https://platform.hiverge.ai/identity",
            organization_id="my-org",
            insecure=True,
        )
        assert manager._token_endpoint == (
            "https://platform.hiverge.ai/identity/realms/my-org/protocol/openid-connect/token"
        )
        assert manager._organization_id == "my-org"
        assert manager._credential_store is mock_store
        assert manager._login_flow is mock_flow

    def test_insecure_flag_disables_ssl_verification_on_session(
        self,
        mock_credential_store: MagicMock,
        mock_login_flow: MagicMock,
    ) -> None:
        """
        Test that insecure=True disables SSL verification on OAuth2 sessions
        created from stored tokens.
        """
        # given
        session_manager = OidcSessionManager(
            organization_id="test-org",
            credential_store=mock_credential_store,
            login_flow=mock_login_flow,
            token_endpoint="https://identity.example.com/realms/test-org/protocol/openid-connect/token",
            insecure=True,
        )
        mock_credential_store.load_token.return_value = {
            "access_token": "stored-token",
            "token_type": "Bearer",
        }

        # when
        session = session_manager.create_session()

        # then
        assert session.verify is False
