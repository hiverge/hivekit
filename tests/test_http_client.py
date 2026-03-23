"""
Unit tests for the HttpClient class and create_http_client factory.
"""

import os
from unittest.mock import MagicMock, patch

import pytest
import requests

from cli.auth.credential_store import CredentialStore
from cli.auth.oidc_flow import OidcLoginFlow
from cli.http_client import (
    AuthenticationError,
    HttpClient,
    create_http_client,
    create_unauthenticated_http_client,
)


@pytest.fixture(name="mock_on_auth_failure")
def _mock_on_auth_failure() -> MagicMock:
    """
    A mock on_auth_failure callback.
    """
    return MagicMock()


class TestHttpClientInit:
    """
    Tests for the `HttpClient` initialization.
    """

    def test_init_with_defaults(self, mock_on_auth_failure: MagicMock) -> None:
        """
        Test that the HttpClient uses the default base URL when none is provided.
        """
        # when
        client = HttpClient(on_auth_failure=mock_on_auth_failure)

        # then
        assert client.base_url == "https://platform.hiverge.ai/api/v1"

    def test_init_with_custom_base_url(self, mock_on_auth_failure: MagicMock) -> None:
        """
        Test initialization with a custom base URL.
        """
        # when
        client = HttpClient(on_auth_failure=mock_on_auth_failure, base_url="https://custom-server.com/api")

        # then
        assert client.base_url == "https://custom-server.com/api"

    def test_init_strips_trailing_slash(self, mock_on_auth_failure: MagicMock) -> None:
        """
        Test that a trailing slash is removed from the base URL.
        """
        # when
        client = HttpClient(on_auth_failure=mock_on_auth_failure, base_url="https://server.com/api/")

        # then
        assert client.base_url == "https://server.com/api"

    @patch.dict(os.environ, {"HIVE_API_ENDPOINT": "https://env-server.com"})
    def test_init_uses_env_variable(self, mock_on_auth_failure: MagicMock) -> None:
        """
        Test that the HIVE_API_ENDPOINT environment variable is used.
        """
        # when
        client = HttpClient(on_auth_failure=mock_on_auth_failure)

        # then
        assert client.base_url == "https://env-server.com"

    def test_init_with_injected_session(self, mock_on_auth_failure: MagicMock) -> None:
        """
        Test that an injected session is used instead of creating a new one.
        """
        # given
        mock_session = MagicMock(spec=requests.Session)

        # when
        client = HttpClient(
            on_auth_failure=mock_on_auth_failure,
            session=mock_session,
            base_url="https://example.com",
        )

        # then
        assert client._session is mock_session

    def test_insecure_passes_verify_false_in_requests(self) -> None:
        """
        Test that insecure=True causes verify=False to be passed in HTTP requests.
        """
        # given
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"experiments": []}
        mock_session.get.return_value = mock_response

        client = HttpClient(
            on_auth_failure=MagicMock(),
            session=mock_session,
            base_url="https://example.com",
            insecure=True,
        )

        # when
        client.list_experiments()

        # then
        mock_session.get.assert_called_once_with(
            "https://example.com/experiments",
            headers={"Content-Type": "application/json"},
            json=None,
            timeout=30,
            verify=False,
        )

    def test_secure_by_default_passes_verify_true(self) -> None:
        """
        Test that insecure defaults to False and verify=True is passed in requests.
        """
        # given
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"experiments": []}
        mock_session.get.return_value = mock_response

        client = HttpClient(
            on_auth_failure=MagicMock(),
            session=mock_session,
            base_url="https://example.com",
        )

        # when
        client.list_experiments()

        # then
        mock_session.get.assert_called_once_with(
            "https://example.com/experiments",
            headers={"Content-Type": "application/json"},
            json=None,
            timeout=30,
            verify=True,
        )


class TestHttpClientCreateExperiment:
    """
    Tests for the `create_experiment` method.
    """

    def test_create_experiment_success(self) -> None:
        """
        Test successful experiment creation.
        """
        # given
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"metadata": {"name": "test-exp"}}
        mock_session.post.return_value = mock_response
        client = HttpClient(
            on_auth_failure=MagicMock(),
            session=mock_session,
            base_url="https://example.com/api/v1",
        )

        # when
        result = client.create_experiment({"metadata": {"name": "test-exp"}})

        # then
        assert result == {"metadata": {"name": "test-exp"}}
        mock_session.post.assert_called_once_with(
            "https://example.com/api/v1/experiments",
            headers={"Content-Type": "application/json"},
            json={"metadata": {"name": "test-exp"}},
            timeout=30,
            verify=True,
        )

    def test_create_experiment_http_error_with_json(self) -> None:
        """
        Test that create_experiment handles an HTTP error with a JSON response.
        """
        # given
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {"error": "Bad request"}
        http_error = requests.exceptions.HTTPError()
        http_error.response = mock_response
        mock_response.raise_for_status.side_effect = http_error
        mock_session.post.return_value = mock_response
        client = HttpClient(
            on_auth_failure=MagicMock(),
            session=mock_session,
            base_url="https://example.com/api/v1",
        )

        # when / then
        with pytest.raises(Exception, match="Failed to create experiment: Bad request"):
            client.create_experiment({"metadata": {"name": "test"}})

    def test_create_experiment_connection_error(self) -> None:
        """
        Test that create_experiment handles connection errors.
        """
        # given
        mock_session = MagicMock()
        mock_session.post.side_effect = requests.exceptions.ConnectionError("Connection failed")
        client = HttpClient(
            on_auth_failure=MagicMock(),
            session=mock_session,
            base_url="https://example.com/api/v1",
        )

        # when / then
        with pytest.raises(Exception, match="Failed to connect to backend server"):
            client.create_experiment({"metadata": {"name": "test"}})


class TestHttpClientGetExperiment:
    """
    Tests for the `get_experiment` method.
    """

    def test_get_experiment_success(self) -> None:
        """
        Test successful get experiment.
        """
        # given
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"metadata": {"name": "test-exp"}}
        mock_session.get.return_value = mock_response
        client = HttpClient(
            on_auth_failure=MagicMock(),
            session=mock_session,
            base_url="https://example.com/api/v1",
        )

        # when
        result = client.get_experiment("test-exp")

        # then
        assert result == {"metadata": {"name": "test-exp"}}
        mock_session.get.assert_called_once_with(
            "https://example.com/api/v1/experiments/test-exp",
            headers={"Content-Type": "application/json"},
            json=None,
            timeout=30,
            verify=True,
        )

    def test_get_experiment_error(self) -> None:
        """
        Test that get_experiment handles errors.
        """
        # given
        mock_session = MagicMock()
        mock_session.get.side_effect = requests.exceptions.RequestException("Error")
        client = HttpClient(
            on_auth_failure=MagicMock(),
            session=mock_session,
            base_url="https://example.com/api/v1",
        )

        # when / then
        with pytest.raises(Exception, match="Failed to get experiment"):
            client.get_experiment("test-exp")


class TestHttpClientListExperiments:
    """
    Tests for the `list_experiments` method.
    """

    def test_list_experiments_success(self) -> None:
        """
        Test successful list experiments.
        """
        # given
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "experiments": [{"metadata": {"name": "exp1"}}, {"metadata": {"name": "exp2"}}]
        }
        mock_session.get.return_value = mock_response
        client = HttpClient(
            on_auth_failure=MagicMock(),
            session=mock_session,
            base_url="https://example.com/api/v1",
        )

        # when
        result = client.list_experiments()

        # then
        assert result == {
            "experiments": [{"metadata": {"name": "exp1"}}, {"metadata": {"name": "exp2"}}]
        }
        mock_session.get.assert_called_once()

    def test_list_experiments_error(self) -> None:
        """
        Test that list_experiments handles errors.
        """
        # given
        mock_session = MagicMock()
        mock_session.get.side_effect = requests.exceptions.RequestException("Error")
        client = HttpClient(
            on_auth_failure=MagicMock(),
            session=mock_session,
            base_url="https://example.com/api/v1",
        )

        # when / then
        with pytest.raises(Exception, match="Failed to list experiments"):
            client.list_experiments()


class TestHttpClientDeleteExperiment:
    """
    Tests for the `delete_experiment` method.
    """

    def test_delete_experiment_success(self) -> None:
        """
        Test successful delete experiment.
        """
        # given
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"message": "Deleted"}
        mock_session.delete.return_value = mock_response
        client = HttpClient(
            on_auth_failure=MagicMock(),
            session=mock_session,
            base_url="https://example.com/api/v1",
        )

        # when
        result = client.delete_experiment("test-exp")

        # then
        assert result == {"message": "Deleted"}
        mock_session.delete.assert_called_once()

    def test_delete_experiment_error(self) -> None:
        """
        Test that delete_experiment handles errors.
        """
        # given
        mock_session = MagicMock()
        mock_session.delete.side_effect = requests.exceptions.RequestException("Error")
        client = HttpClient(
            on_auth_failure=MagicMock(),
            session=mock_session,
            base_url="https://example.com/api/v1",
        )

        # when / then
        with pytest.raises(Exception, match="Failed to delete experiment"):
            client.delete_experiment("test-exp")


class TestAuthenticationHandling:
    """
    Tests for 401 authentication error handling in the `HttpClient`.
    """

    def test_401_with_reauth_raising_error(self) -> None:
        """
        Test that a 401 response triggers the on_auth_failure callback, and when
        it raises, an AuthenticationError is propagated.
        """
        # given
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_session.get.return_value = mock_response
        mock_reauth = MagicMock(side_effect=Exception("Reauth failed"))

        client = HttpClient(
            on_auth_failure=mock_reauth,
            session=mock_session,
            base_url="https://example.com/api/v1",
        )

        # when / then
        with pytest.raises(AuthenticationError, match="credentials have expired"):
            client.list_experiments()
        mock_reauth.assert_called_once()

    def test_401_with_successful_reauth(self) -> None:
        """
        Test that a 401 response triggers re-authentication and retries the request
        successfully.
        """
        # given
        mock_session = MagicMock()
        mock_401 = MagicMock()
        mock_401.status_code = 401
        mock_200 = MagicMock()
        mock_200.status_code = 200
        mock_200.json.return_value = {"experiments": []}
        mock_session.get.return_value = mock_401

        new_session = MagicMock()
        new_session.get.return_value = mock_200
        mock_reauth = MagicMock(return_value=new_session)

        client = HttpClient(
            on_auth_failure=mock_reauth,
            session=mock_session,
            base_url="https://example.com/api/v1",
        )

        # when
        result = client.list_experiments()

        # then
        assert result == {"experiments": []}
        mock_reauth.assert_called_once()
        new_session.get.assert_called_once()

    def test_401_with_failed_reauth_raises_authentication_error(self) -> None:
        """
        Test that a 401 response followed by a failed re-authentication attempt
        raises AuthenticationError.
        """
        # given
        mock_session = MagicMock()
        mock_401 = MagicMock()
        mock_401.status_code = 401
        mock_session.get.return_value = mock_401
        mock_reauth = MagicMock(side_effect=Exception("Login failed"))

        client = HttpClient(
            on_auth_failure=mock_reauth,
            session=mock_session,
            base_url="https://example.com/api/v1",
        )

        # when / then
        with pytest.raises(AuthenticationError, match="credentials have expired"):
            client.list_experiments()

    def test_401_after_reauth_retry_raises_authentication_error(self) -> None:
        """
        Test that a 401 on the retry attempt (after successful re-auth) raises
        AuthenticationError.
        """
        # given
        mock_session = MagicMock()
        mock_401 = MagicMock()
        mock_401.status_code = 401
        mock_session.get.return_value = mock_401

        new_session = MagicMock()
        new_session.get.return_value = mock_401
        mock_reauth = MagicMock(return_value=new_session)

        client = HttpClient(
            on_auth_failure=mock_reauth,
            session=mock_session,
            base_url="https://example.com/api/v1",
        )

        # when / then
        with pytest.raises(AuthenticationError, match="credentials have expired"):
            client.list_experiments()

    def test_insecure_passes_verify_false_after_reauth(self) -> None:
        """
        Test that insecure=True passes verify=False to the new session's
        requests after re-authentication.
        """
        # given
        mock_session = MagicMock()
        mock_401 = MagicMock()
        mock_401.status_code = 401
        mock_200 = MagicMock()
        mock_200.status_code = 200
        mock_200.json.return_value = {"experiments": []}
        mock_session.get.return_value = mock_401

        new_session = MagicMock()
        new_session.get.return_value = mock_200
        mock_reauth = MagicMock(return_value=new_session)

        client = HttpClient(
            on_auth_failure=mock_reauth,
            session=mock_session,
            base_url="https://example.com/api/v1",
            insecure=True,
        )

        # when
        client.list_experiments()

        # then
        mock_session.get.assert_called_once_with(
            "https://example.com/api/v1/experiments",
            headers={"Content-Type": "application/json"},
            json=None,
            timeout=30,
            verify=False,
        )
        new_session.get.assert_called_once_with(
            "https://example.com/api/v1/experiments",
            headers={"Content-Type": "application/json"},
            json=None,
            timeout=30,
            verify=False,
        )


class TestCreateHttpClient:
    """
    Tests for the `create_http_client` and `create_unauthenticated_http_client` factory functions.
    """

    def test_unauthenticated_returns_plain_client(self) -> None:
        """
        Test that create_unauthenticated_http_client returns an HttpClient with a plain session.
        """
        # when
        client = create_unauthenticated_http_client(
            base_url="https://example.com/api/v1",
        )

        # then
        assert client.base_url == "https://example.com/api/v1"
        assert client._on_auth_failure is not None

    @patch("cli.http_client.OidcLoginFlow")
    def test_with_stored_token(self, mock_flow_class: MagicMock) -> None:
        """
        Test that a stored token is loaded and used to create an OAuth2Session.
        """
        # given
        mock_credential_store = MagicMock(spec=CredentialStore)
        mock_credential_store.load_token.return_value = {
            "access_token": "stored-token",
            "token_type": "Bearer",
        }
        mock_login_flow = MagicMock(spec=OidcLoginFlow)

        # when
        client = create_http_client(
            base_url="https://platform.hiverge.ai/api/v1",
            insecure=False,
            organization_id="my-org",
            credential_store=mock_credential_store,
            login_flow=mock_login_flow,
        )

        # then
        mock_credential_store.load_token.assert_called_once_with(organization_id="my-org")
        assert client.base_url == "https://platform.hiverge.ai/api/v1"

    @patch("cli.http_client.OidcLoginFlow")
    def test_no_stored_token_triggers_auto_login(self, mock_flow_class: MagicMock) -> None:
        """
        Test that when no token is stored, auto-login is attempted via the login flow.
        """
        # given
        mock_credential_store = MagicMock(spec=CredentialStore)
        mock_credential_store.load_token.return_value = None
        mock_login_flow = MagicMock(spec=OidcLoginFlow)
        mock_login_flow.login.return_value = {
            "access_token": "fresh-token",
            "token_type": "Bearer",
        }

        # when
        client = create_http_client(
            base_url="https://platform.hiverge.ai/api/v1",
            insecure=False,
            organization_id="my-org",
            credential_store=mock_credential_store,
            login_flow=mock_login_flow,
        )

        # then
        mock_login_flow.login.assert_called_once()
        assert client._on_auth_failure is not None

    @patch("cli.http_client.OidcLoginFlow")
    def test_no_stored_token_login_failure_raises_authentication_error(
        self, mock_flow_class: MagicMock
    ) -> None:
        """
        Test that when no token is stored and auto-login fails, an
        AuthenticationError is raised.
        """
        # given
        mock_credential_store = MagicMock(spec=CredentialStore)
        mock_credential_store.load_token.return_value = None
        mock_login_flow = MagicMock(spec=OidcLoginFlow)
        mock_login_flow.login.side_effect = Exception("Browser failed")

        # when / then
        with pytest.raises(AuthenticationError, match="Login failed"):
            create_http_client(
                base_url="https://platform.hiverge.ai/api/v1",
                insecure=False,
                organization_id="my-org",
                credential_store=mock_credential_store,
                login_flow=mock_login_flow,
            )
