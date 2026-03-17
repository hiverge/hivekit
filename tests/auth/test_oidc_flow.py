"""
Tests for the OIDC login flow in the auth module.
"""

from unittest.mock import MagicMock

import pytest

from cli.auth.credential_store import CredentialStore
from cli.auth.oidc_flow import OidcLoginFlow


@pytest.fixture(name="mock_credential_store")
def _mock_credential_store() -> MagicMock:
    """
    A mock credential store.
    """
    return MagicMock(spec=CredentialStore)


@pytest.fixture(name="mock_callback_server")
def _mock_callback_server() -> MagicMock:
    """
    A mock callback server that returns a simulated authorization callback URL.
    """
    server = MagicMock()
    server.redirect_uri = "http://127.0.0.1:54422/callback"
    server.wait_for_callback.return_value = (
        "http://127.0.0.1:54422/callback?code=auth-code-123&state=test-state"
    )
    return server


@pytest.fixture(name="mock_session")
def _mock_session() -> MagicMock:
    """
    A mock OAuth2Session.
    """
    session = MagicMock()
    session.create_authorization_url.return_value = (
        "https://identity.example.com/auth?client_id=hiverge&state=test-state",
        "test-state",
    )
    session.fetch_token.return_value = {
        "access_token": "new-access-token",
        "refresh_token": "new-refresh-token",
        "token_type": "Bearer",
        "expires_in": 300,
    }
    return session


class TestOidcLoginFlow:
    """
    Tests for the `OidcLoginFlow` class.
    """

    def test_login_opens_browser_with_authorization_url(
        self,
        mock_credential_store: MagicMock,
        mock_callback_server: MagicMock,
        mock_session: MagicMock,
    ) -> None:
        """
        Test that the login flow opens the browser with the correct authorization URL.
        """
        # given
        mock_browser_opener = MagicMock()
        flow = OidcLoginFlow(
            identity_base_url="https://identity.example.com",
            organization_id="my-org",
            credential_store=mock_credential_store,
            browser_opener=mock_browser_opener,
            callback_server_factory=lambda: mock_callback_server,
            session_factory=lambda **kwargs: mock_session,
        )

        # when
        flow.login()

        # then
        mock_browser_opener.assert_called_once_with(
            "https://identity.example.com/auth?client_id=hiverge&state=test-state"
        )

    def test_login_exchanges_code_for_tokens(
        self,
        mock_credential_store: MagicMock,
        mock_callback_server: MagicMock,
        mock_session: MagicMock,
    ) -> None:
        """
        Test that the login flow exchanges the authorization code for tokens.
        """
        # given
        flow = OidcLoginFlow(
            identity_base_url="https://identity.example.com",
            organization_id="my-org",
            credential_store=mock_credential_store,
            browser_opener=MagicMock(),
            callback_server_factory=lambda: mock_callback_server,
            session_factory=lambda **kwargs: mock_session,
        )

        # when
        flow.login()

        # then
        mock_session.fetch_token.assert_called_once_with(
            url="https://identity.example.com/realms/my-org/protocol/openid-connect/token",
            authorization_response="http://127.0.0.1:54422/callback?code=auth-code-123&state=test-state",
        )

    def test_login_saves_tokens_to_credential_store(
        self,
        mock_credential_store: MagicMock,
        mock_callback_server: MagicMock,
        mock_session: MagicMock,
    ) -> None:
        """
        Test that the login flow saves the fetched tokens to the credential store.
        """
        # given
        flow = OidcLoginFlow(
            identity_base_url="https://identity.example.com",
            organization_id="my-org",
            credential_store=mock_credential_store,
            browser_opener=MagicMock(),
            callback_server_factory=lambda: mock_callback_server,
            session_factory=lambda **kwargs: mock_session,
        )

        # when
        flow.login()

        # then
        mock_credential_store.save_token.assert_called_once_with(
            organization_id="my-org",
            token={
                "access_token": "new-access-token",
                "refresh_token": "new-refresh-token",
                "token_type": "Bearer",
                "expires_in": 300,
            },
        )

    def test_login_returns_token(
        self,
        mock_credential_store: MagicMock,
        mock_callback_server: MagicMock,
        mock_session: MagicMock,
    ) -> None:
        """
        Test that the login flow returns the fetched token dict.
        """
        # given
        flow = OidcLoginFlow(
            identity_base_url="https://identity.example.com",
            organization_id="my-org",
            credential_store=mock_credential_store,
            browser_opener=MagicMock(),
            callback_server_factory=lambda: mock_callback_server,
            session_factory=lambda **kwargs: mock_session,
        )

        # when
        result = flow.login()

        # then
        assert result == {
            "access_token": "new-access-token",
            "refresh_token": "new-refresh-token",
            "token_type": "Bearer",
            "expires_in": 300,
        }

    def test_login_shuts_down_callback_server(
        self,
        mock_credential_store: MagicMock,
        mock_callback_server: MagicMock,
        mock_session: MagicMock,
    ) -> None:
        """
        Test that the callback server is shut down after the login flow completes.
        """
        # given
        flow = OidcLoginFlow(
            identity_base_url="https://identity.example.com",
            organization_id="my-org",
            credential_store=mock_credential_store,
            browser_opener=MagicMock(),
            callback_server_factory=lambda: mock_callback_server,
            session_factory=lambda **kwargs: mock_session,
        )

        # when
        flow.login()

        # then
        mock_callback_server.shutdown.assert_called_once()

    def test_login_prints_url_when_browser_fails(
        self,
        mock_credential_store: MagicMock,
        mock_callback_server: MagicMock,
        mock_session: MagicMock,
    ) -> None:
        """
        Test that when the browser cannot be opened, the authorization URL is
        printed to the console instead.
        """
        # given
        mock_browser_opener = MagicMock(side_effect=Exception("No browser"))
        mock_console = MagicMock()
        flow = OidcLoginFlow(
            identity_base_url="https://identity.example.com",
            organization_id="my-org",
            credential_store=mock_credential_store,
            browser_opener=mock_browser_opener,
            callback_server_factory=lambda: mock_callback_server,
            session_factory=lambda **kwargs: mock_session,
            console=mock_console,
        )

        # when
        result = flow.login()

        # then — login should still succeed
        assert result == {
            "access_token": "new-access-token",
            "refresh_token": "new-refresh-token",
            "token_type": "Bearer",
            "expires_in": 300,
        }
        # The console should have been used to print the URL
        mock_console.print.assert_any_call(
            "[yellow]Please open the following URL in your browser:[/yellow]"
        )

    def test_login_creates_session_with_correct_params(
        self,
        mock_credential_store: MagicMock,
        mock_callback_server: MagicMock,
        mock_session: MagicMock,
    ) -> None:
        """
        Test that the OAuth2Session is created with the correct parameters.
        """
        # given
        captured_kwargs = {}

        def capturing_factory(**kwargs):
            captured_kwargs.update(kwargs)
            return mock_session

        flow = OidcLoginFlow(
            identity_base_url="https://identity.example.com",
            organization_id="my-org",
            credential_store=mock_credential_store,
            browser_opener=MagicMock(),
            callback_server_factory=lambda: mock_callback_server,
            session_factory=capturing_factory,
        )

        # when
        flow.login()

        # then
        assert captured_kwargs["client_id"] == "hiverge"
        assert captured_kwargs["redirect_uri"] == "http://127.0.0.1:54422/callback"
        assert captured_kwargs["scope"] == "openid"
        assert captured_kwargs["code_challenge_method"] == "S256"

    def test_login_shuts_down_server_on_error(
        self,
        mock_credential_store: MagicMock,
        mock_callback_server: MagicMock,
        mock_session: MagicMock,
    ) -> None:
        """
        Test that the callback server is shut down even when an error occurs
        during the login flow.
        """
        # given
        mock_session.fetch_token.side_effect = Exception("Token exchange failed")
        flow = OidcLoginFlow(
            identity_base_url="https://identity.example.com",
            organization_id="my-org",
            credential_store=mock_credential_store,
            browser_opener=MagicMock(),
            callback_server_factory=lambda: mock_callback_server,
            session_factory=lambda **kwargs: mock_session,
        )

        # when
        with pytest.raises(Exception, match="Token exchange failed"):
            flow.login()

        # then
        mock_callback_server.shutdown.assert_called_once()

    def test_insecure_disables_ssl_on_session(
        self,
        mock_credential_store: MagicMock,
        mock_callback_server: MagicMock,
        mock_session: MagicMock,
    ) -> None:
        """
        Test that insecure=True sets verify=False on the OAuth2Session used
        for the token exchange.
        """
        # given
        flow = OidcLoginFlow(
            identity_base_url="https://identity.example.com",
            organization_id="my-org",
            credential_store=mock_credential_store,
            browser_opener=MagicMock(),
            callback_server_factory=lambda: mock_callback_server,
            session_factory=lambda **kwargs: mock_session,
            insecure=True,
        )

        # when
        flow.login()

        # then
        assert mock_session.verify is False

    def test_secure_by_default_does_not_set_verify(
        self,
        mock_credential_store: MagicMock,
        mock_callback_server: MagicMock,
        mock_session: MagicMock,
    ) -> None:
        """
        Test that verify is not set to False on the session when insecure
        is not specified.
        """
        # given
        mock_session.verify = True
        flow = OidcLoginFlow(
            identity_base_url="https://identity.example.com",
            organization_id="my-org",
            credential_store=mock_credential_store,
            browser_opener=MagicMock(),
            callback_server_factory=lambda: mock_callback_server,
            session_factory=lambda **kwargs: mock_session,
        )

        # when
        flow.login()

        # then
        assert mock_session.verify is True
