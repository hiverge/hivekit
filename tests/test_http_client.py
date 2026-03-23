"""
Unit tests for the HttpClient class and the build_http_client factory.
"""

import os
from unittest.mock import MagicMock, patch

import pytest
import requests

from cli.http_client import (
    AuthenticationError,
    HttpClient,
    build_http_client,
)


@pytest.fixture(name="mock_on_auth_failure")
def _mock_on_auth_failure() -> MagicMock:
    """
    A mock on_auth_failure callback.
    """
    return MagicMock()


@pytest.fixture(name="mock_session")
def _mock_session() -> MagicMock:
    """
    A mock HTTP session.
    """
    return MagicMock(spec=requests.Session)


@pytest.fixture(name="http_client")
def _http_client(mock_on_auth_failure: MagicMock, mock_session: MagicMock) -> HttpClient:
    """
    An HttpClient configured with a mock session and mock auth callback.
    """
    return HttpClient(
        on_auth_failure=mock_on_auth_failure,
        session=mock_session,
        base_url="https://example.com/api/v1",
    )


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

    def test_create_experiment_success(self, http_client: HttpClient, mock_session: MagicMock) -> None:
        """
        Test successful experiment creation.
        """
        # given
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"metadata": {"name": "test-exp"}}
        mock_session.post.return_value = mock_response

        # when
        result = http_client.create_experiment({"metadata": {"name": "test-exp"}})

        # then
        assert result == {"metadata": {"name": "test-exp"}}
        mock_session.post.assert_called_once_with(
            "https://example.com/api/v1/experiments",
            headers={"Content-Type": "application/json"},
            json={"metadata": {"name": "test-exp"}},
            timeout=30,
            verify=True,
        )

    def test_create_experiment_http_error_with_json(self, http_client: HttpClient, mock_session: MagicMock) -> None:
        """
        Test that create_experiment handles an HTTP error with a JSON response.
        """
        # given
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {"error": "Bad request"}
        http_error = requests.exceptions.HTTPError()
        http_error.response = mock_response
        mock_response.raise_for_status.side_effect = http_error
        mock_session.post.return_value = mock_response

        # when / then
        with pytest.raises(Exception, match="Failed to create experiment: Bad request"):
            http_client.create_experiment({"metadata": {"name": "test"}})

    def test_create_experiment_connection_error(self, http_client: HttpClient, mock_session: MagicMock) -> None:
        """
        Test that create_experiment handles connection errors.
        """
        # given
        mock_session.post.side_effect = requests.exceptions.ConnectionError("Connection failed")

        # when / then
        with pytest.raises(Exception, match="Failed to connect to backend server"):
            http_client.create_experiment({"metadata": {"name": "test"}})


class TestHttpClientGetExperiment:
    """
    Tests for the `get_experiment` method.
    """

    def test_get_experiment_success(self, http_client: HttpClient, mock_session: MagicMock) -> None:
        """
        Test successful get experiment.
        """
        # given
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"metadata": {"name": "test-exp"}}
        mock_session.get.return_value = mock_response

        # when
        result = http_client.get_experiment("test-exp")

        # then
        assert result == {"metadata": {"name": "test-exp"}}
        mock_session.get.assert_called_once_with(
            "https://example.com/api/v1/experiments/test-exp",
            headers={"Content-Type": "application/json"},
            json=None,
            timeout=30,
            verify=True,
        )

    def test_get_experiment_error(self, http_client: HttpClient, mock_session: MagicMock) -> None:
        """
        Test that get_experiment handles errors.
        """
        # given
        mock_session.get.side_effect = requests.exceptions.RequestException("Error")

        # when / then
        with pytest.raises(Exception, match="Failed to get experiment"):
            http_client.get_experiment("test-exp")


class TestHttpClientListExperiments:
    """
    Tests for the `list_experiments` method.
    """

    def test_list_experiments_success(self, http_client: HttpClient, mock_session: MagicMock) -> None:
        """
        Test successful list experiments.
        """
        # given
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "experiments": [{"metadata": {"name": "exp1"}}, {"metadata": {"name": "exp2"}}]
        }
        mock_session.get.return_value = mock_response

        # when
        result = http_client.list_experiments()

        # then
        assert result == {
            "experiments": [{"metadata": {"name": "exp1"}}, {"metadata": {"name": "exp2"}}]
        }
        mock_session.get.assert_called_once_with(
            "https://example.com/api/v1/experiments",
            headers={"Content-Type": "application/json"},
            json=None,
            timeout=30,
            verify=True,
        )

    def test_list_experiments_error(self, http_client: HttpClient, mock_session: MagicMock) -> None:
        """
        Test that list_experiments handles errors.
        """
        # given
        mock_session.get.side_effect = requests.exceptions.RequestException("Error")

        # when / then
        with pytest.raises(Exception, match="Failed to list experiments"):
            http_client.list_experiments()


class TestHttpClientDeleteExperiment:
    """
    Tests for the `delete_experiment` method.
    """

    def test_delete_experiment_success(self, http_client: HttpClient, mock_session: MagicMock) -> None:
        """
        Test successful delete experiment.
        """
        # given
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"message": "Deleted"}
        mock_session.delete.return_value = mock_response

        # when
        result = http_client.delete_experiment("test-exp")

        # then
        assert result == {"message": "Deleted"}
        mock_session.delete.assert_called_once_with(
            "https://example.com/api/v1/experiments/test-exp",
            headers={"Content-Type": "application/json"},
            json=None,
            timeout=30,
            verify=True,
        )

    def test_delete_experiment_error(self, http_client: HttpClient, mock_session: MagicMock) -> None:
        """
        Test that delete_experiment handles errors.
        """
        # given
        mock_session.delete.side_effect = requests.exceptions.RequestException("Error")

        # when / then
        with pytest.raises(Exception, match="Failed to delete experiment"):
            http_client.delete_experiment("test-exp")


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


class TestBuildHttpClient:
    """
    Tests for the `build_http_client` factory function.
    """

    @patch("cli.http_client.get_api_endpoint", return_value="https://platform.hiverge.ai/api/v1")
    def test_no_auth_returns_unauthenticated_client(self, mock_get_endpoint: MagicMock) -> None:
        """
        Test that build_http_client with no_auth=True returns an unauthenticated client.
        """
        # when
        client = build_http_client(no_auth=True)

        # then
        assert client.base_url == "https://platform.hiverge.ai/api/v1"
        mock_get_endpoint.assert_called_once()
        # The on_auth_failure callback should raise AuthenticationError
        with pytest.raises(AuthenticationError, match="Authentication is not configured"):
            client._on_auth_failure()

    @patch("cli.http_client.get_api_endpoint", return_value="https://platform.hiverge.ai/api/v1")
    @patch("cli.http_client.os.path.exists", return_value=False)
    def test_no_config_file_raises_authentication_error(
        self, mock_exists: MagicMock, mock_get_endpoint: MagicMock
    ) -> None:
        """
        Test that build_http_client raises AuthenticationError when no config
        file exists and no organization_id is provided.
        """
        # when / then
        with pytest.raises(AuthenticationError, match="No organization ID configured"):
            build_http_client()

    @patch("cli.http_client.OidcLoginFlow")
    @patch("cli.http_client.create_credential_store")
    @patch("cli.http_client.get_api_endpoint", return_value="https://platform.hiverge.ai/api/v1")
    def test_with_organization_id_and_stored_token(
        self,
        mock_get_endpoint: MagicMock,
        mock_create_store: MagicMock,
        mock_flow_class: MagicMock,
    ) -> None:
        """
        Test that build_http_client with an explicit organization_id and a stored
        token creates an authenticated client.
        """
        # given
        mock_store = MagicMock()
        mock_store.load_token.return_value = {
            "access_token": "stored-token",
            "token_type": "Bearer",
        }
        mock_create_store.return_value = mock_store

        # when
        client = build_http_client(organization_id="my-org")

        # then
        assert client.base_url == "https://platform.hiverge.ai/api/v1"
        mock_store.load_token.assert_called_once_with(organization_id="my-org")

    @patch("cli.http_client.OidcLoginFlow")
    @patch("cli.http_client.create_credential_store")
    @patch("cli.http_client.get_api_endpoint", return_value="https://platform.hiverge.ai/api/v1")
    def test_no_stored_token_triggers_auto_login(
        self,
        mock_get_endpoint: MagicMock,
        mock_create_store: MagicMock,
        mock_flow_class: MagicMock,
    ) -> None:
        """
        Test that when no token is stored, auto-login is attempted via the login flow.
        """
        # given
        mock_store = MagicMock()
        mock_store.load_token.return_value = None
        mock_create_store.return_value = mock_store

        mock_flow = MagicMock()
        mock_flow.login.return_value = {
            "access_token": "fresh-token",
            "token_type": "Bearer",
        }
        mock_flow_class.return_value = mock_flow

        # when
        client = build_http_client(organization_id="my-org")

        # then
        mock_flow.login.assert_called_once()
        assert client.base_url == "https://platform.hiverge.ai/api/v1"

    @patch("cli.http_client.OidcLoginFlow")
    @patch("cli.http_client.create_credential_store")
    @patch("cli.http_client.get_api_endpoint", return_value="https://platform.hiverge.ai/api/v1")
    def test_no_stored_token_login_failure_raises_authentication_error(
        self,
        mock_get_endpoint: MagicMock,
        mock_create_store: MagicMock,
        mock_flow_class: MagicMock,
    ) -> None:
        """
        Test that when no token is stored and auto-login fails, an
        AuthenticationError is raised.
        """
        # given
        mock_store = MagicMock()
        mock_store.load_token.return_value = None
        mock_create_store.return_value = mock_store

        mock_flow = MagicMock()
        mock_flow.login.side_effect = Exception("Browser failed")
        mock_flow_class.return_value = mock_flow

        # when / then
        with pytest.raises(AuthenticationError, match="Login failed"):
            build_http_client(organization_id="my-org")

    @patch("cli.http_client.get_api_endpoint", return_value="https://platform.hiverge.ai/api/v1")
    def test_insecure_flag_is_passed_through(self, mock_get_endpoint: MagicMock) -> None:
        """
        Test that the insecure flag is passed through to the unauthenticated client.
        """
        # when
        client = build_http_client(no_auth=True, insecure=True)

        # then
        assert client._insecure is True

    @patch("cli.http_client.OidcLoginFlow")
    @patch("cli.http_client.create_credential_store")
    @patch("cli.http_client.get_api_endpoint", return_value="https://platform.hiverge.ai/api/v1")
    @patch("builtins.open", create=True)
    @patch("cli.http_client.os.path.exists", return_value=True)
    def test_reads_organization_id_from_config_file(
        self,
        mock_exists: MagicMock,
        mock_open: MagicMock,
        mock_get_endpoint: MagicMock,
        mock_create_store: MagicMock,
        mock_flow_class: MagicMock,
    ) -> None:
        """
        Test that build_http_client reads the organization_id from the config file
        when not provided explicitly.
        """
        # given
        import io

        mock_open.return_value.__enter__ = lambda s: io.StringIO("organization_id: file-org\n")
        mock_open.return_value.__exit__ = MagicMock(return_value=False)

        mock_store = MagicMock()
        mock_store.load_token.return_value = {
            "access_token": "token",
            "token_type": "Bearer",
        }
        mock_create_store.return_value = mock_store

        # when
        client = build_http_client()

        # then
        mock_store.load_token.assert_called_once_with(organization_id="file-org")
        assert client.base_url == "https://platform.hiverge.ai/api/v1"
