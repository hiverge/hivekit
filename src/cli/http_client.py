"""
HTTP client for communicating with the Hive backend server.
"""

import logging
import os
from typing import Any, Callable, Dict, Optional

import requests
from authlib.integrations.requests_client import OAuth2Session
from rich.console import Console

from cli.auth.auth_utils import get_machine_id
from cli.auth.credential_store import CredentialStore, create_credential_store
from cli.auth.oidc_flow import OidcLoginFlow
from cli.config import load_organization_id
from cli.utils.config_paths import get_config_dir, get_config_path
from cli.utils.url_utils import build_oidc_endpoints, derive_identity_base_url, get_api_endpoint

console = Console()
logger = logging.getLogger("hivekit")

_HTTP_UNAUTHORIZED = 401


class AuthenticationError(Exception):
    """
    Raised when authentication fails and cannot be recovered automatically.
    """


class HttpClient:
    """
    HTTP client for communicating with the Hive backend server.
    """

    def __init__(
        self,
        on_auth_failure: Callable[[], requests.Session],
        base_url: str = "",
        session: Optional[requests.Session] = None,
        insecure: bool = False,
    ) -> None:
        """
        Initialize the HTTP client.

        Args:
            on_auth_failure: Callback invoked on 401 responses. Should attempt
                re-authentication and return a new session.
            base_url: Base URL of the backend server (defaults to the HIVE_API_ENDPOINT
                environment variable or the standard platform URL).
            session: Pre-configured HTTP session for making requests.
            insecure: If True, disable SSL certificate verification on all requests.
        """
        self.base_url = (base_url or get_api_endpoint()).rstrip("/")
        self._session = session or requests.Session()
        self._on_auth_failure = on_auth_failure
        self._insecure = insecure

    def create_experiment(self, experiment_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new experiment.

        Args:
            experiment_data: Experiment CRD data to send.

        Returns:
            Created experiment data from the server.

        Raises:
            AuthenticationError: If the request receives a 401 that cannot be recovered.
            Exception: If the request fails for other reasons.
        """
        url = f"{self.base_url}/experiments"
        headers = self._get_headers()

        try:
            response = self._request(method="post", url=url, headers=headers, json=experiment_data)
            response.raise_for_status()
            return response.json()
        except AuthenticationError:
            raise
        except requests.exceptions.HTTPError as e:
            error_msg = f"Failed to create experiment: {e}"
            if e.response is not None:
                try:
                    error_detail = e.response.json()
                    if "error" in error_detail:
                        error_msg = f"Failed to create experiment: {error_detail['error']}"
                except Exception:
                    error_msg = f"Failed to create experiment: {e.response.text}"
            raise Exception(error_msg) from e
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to connect to backend server at {url}: {e}") from e

    def get_experiment(self, name: str) -> Dict[str, Any]:
        """
        Get an experiment by name.

        Args:
            name: Experiment name.

        Returns:
            Experiment data from the server.

        Raises:
            AuthenticationError: If the request receives a 401 that cannot be recovered.
            Exception: If the request fails for other reasons.
        """
        url = f"{self.base_url}/experiments/{name}"
        headers = self._get_headers()

        try:
            response = self._request(method="get", url=url, headers=headers)
            response.raise_for_status()
            return response.json()
        except AuthenticationError:
            raise
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to get experiment: {e}") from e

    def list_experiments(self) -> Dict[str, Any]:
        """
        List experiments.

        Returns:
            List of experiments from the server.

        Raises:
            AuthenticationError: If the request receives a 401 that cannot be recovered.
            Exception: If the request fails for other reasons.
        """
        url = f"{self.base_url}/experiments"
        headers = self._get_headers()

        try:
            response = self._request(method="get", url=url, headers=headers)
            response.raise_for_status()
            return response.json()
        except AuthenticationError:
            raise
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to list experiments: {e}") from e

    def delete_experiment(self, name: str) -> Dict[str, Any]:
        """
        Delete an experiment.

        Args:
            name: Experiment name.

        Returns:
            Response from the server.

        Raises:
            AuthenticationError: If the request receives a 401 that cannot be recovered.
            Exception: If the request fails for other reasons.
        """
        url = f"{self.base_url}/experiments/{name}"
        headers = self._get_headers()

        try:
            response = self._request(method="delete", url=url, headers=headers)
            response.raise_for_status()
            return response.json()
        except AuthenticationError:
            raise
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to delete experiment: {e}") from e

    def _get_headers(self) -> Dict[str, str]:
        """
        Get common headers for all requests.
        """
        return {"Content-Type": "application/json"}

    def _request(
        self,
        method: str,
        url: str,
        headers: Dict[str, str],
        json: Optional[Dict[str, Any]] = None,
    ) -> requests.Response:
        """
        Make an HTTP request, automatically retrying once on 401 by invoking
        the on_auth_failure callback.
        """
        response = self._send_request(method, url, headers, json)
        if response.status_code == _HTTP_UNAUTHORIZED:
            return self._retry_with_reauth(method, url, headers, json)
        return response

    def _send_request(
        self,
        method: str,
        url: str,
        headers: Dict[str, str],
        json: Optional[Dict[str, Any]] = None,
    ) -> requests.Response:
        """
        Send a single HTTP request.
        """
        return getattr(self._session, method)(
            url, headers=headers, json=json, timeout=30, verify=not self._insecure
        )

    def _retry_with_reauth(
        self,
        method: str,
        url: str,
        headers: Dict[str, str],
        json: Optional[Dict[str, Any]] = None,
    ) -> requests.Response:
        """
        Attempt re-authentication and retry the failed request.
        """
        logger.info("Received 401 response. Attempting to re-authenticate.")
        try:
            self._session = self._on_auth_failure()
        except Exception as e:
            raise AuthenticationError(
                "Your credentials have expired. Please run 'hive login' to re-authenticate."
            ) from e
        response = self._send_request(method, url, headers, json)
        if response.status_code == _HTTP_UNAUTHORIZED:
            raise AuthenticationError(
                "Your credentials have expired. Please run 'hive login' to re-authenticate."
            )
        return response


def _create_unauthenticated_http_client(
    base_url: str, insecure: bool = False
) -> HttpClient:
    """
    Create an HttpClient without authentication.

    Args:
        base_url: Base URL of the backend server.
        insecure: If True, disable SSL certificate verification.
    """

    def _raise_auth_error() -> requests.Session:
        raise AuthenticationError(
            "Authentication is not configured. Please run 'hive login' to authenticate."
        )

    return HttpClient(
        on_auth_failure=_raise_auth_error,
        base_url=base_url,
        session=requests.Session(),
        insecure=insecure,
    )


def _create_http_client(
    base_url: str,
    insecure: bool,
    organization_id: str,
    credential_store: CredentialStore,
    login_flow: OidcLoginFlow,
) -> HttpClient:
    """
    Create an HttpClient with OIDC authentication.

    Loads any stored token from the credential store, or triggers an auto-login
    via the provided login flow if no token is available.

    Args:
        base_url: Base URL of the backend server.
        insecure: If True, disable SSL certificate verification.
        organization_id: The organization ID for token storage.
        credential_store: The credential store for loading/saving tokens.
        login_flow: The OIDC login flow for authentication and re-authentication.

    Returns:
        A configured HttpClient instance.
    """

    def _re_authenticate() -> requests.Session:
        """
        Attempt to re-authenticate via the OIDC login flow and return
        a new session with the fresh token.
        """
        logger.info(f"Starting OIDC login flow for organization '{organization_id}'.")
        token = login_flow.login()
        endpoints = build_oidc_endpoints(
            identity_base_url=derive_identity_base_url(api_endpoint=base_url),
            organization_id=organization_id,
        )
        return OAuth2Session(
            client_id="hiverge",
            token=token,
            token_endpoint=endpoints["token_endpoint"],
        )

    token = credential_store.load_token(organization_id=organization_id)
    if token is not None:
        logger.info(f"Loaded stored token for organization '{organization_id}'.")
        endpoints = build_oidc_endpoints(
            identity_base_url=derive_identity_base_url(api_endpoint=base_url),
            organization_id=organization_id,
        )
        session = OAuth2Session(
            client_id="hiverge",
            token=token,
            token_endpoint=endpoints["token_endpoint"],
            update_token=lambda new_token, **kwargs: credential_store.save_token(
                organization_id=organization_id, token=new_token
            ),
        )
    else:
        logger.info(f"No stored token available for organization '{organization_id}'. Login is required.")
        try:
            session = _re_authenticate()
        except Exception as e:
            raise AuthenticationError(
                "Login failed. Please run 'hive login' to authenticate."
            ) from e

    return HttpClient(
        on_auth_failure=_re_authenticate,
        base_url=base_url,
        session=session,
        insecure=insecure,
    )


def build_http_client(
    organization_id: Optional[str] = None,
    no_auth: bool = False,
    insecure: bool = False,
) -> HttpClient:
    """
    Build an HttpClient from configuration, setting up authentication if needed.

    When authentication is enabled (no_auth=False), the organization_id is required.
    If it is not provided, the function reads it from the config file. If no
    organization ID can be determined, an AuthenticationError is raised.

    Args:
        organization_id: The organization ID for authentication. Required when
            no_auth is False, unless it can be read from the config file.
        no_auth: If True, skip authentication entirely. Defaults to False.
        insecure: If True, disable SSL certificate verification. Defaults to False.

    Returns:
        A configured HttpClient instance.

    Raises:
        AuthenticationError: If no organization ID can be determined when
            authentication is enabled.
    """
    base_url = get_api_endpoint()

    if no_auth:
        return _create_unauthenticated_http_client(base_url=base_url, insecure=insecure)

    # Resolve organization_id from config if not provided
    if organization_id is None:
        if os.path.exists(get_config_path()):
            organization_id = load_organization_id(file_path=get_config_path())

    if organization_id is None:
        raise AuthenticationError(
            "No organization ID configured. Please run 'hive init' to set up your configuration."
        )

    credential_store = create_credential_store(
        clients_dir=os.path.join(get_config_dir(), "clients"),
        machine_id_func=get_machine_id,
    )
    identity_base_url = derive_identity_base_url(api_endpoint=base_url)
    login_flow = OidcLoginFlow(
        identity_base_url=identity_base_url,
        organization_id=organization_id,
        credential_store=credential_store,
        insecure=insecure,
    )

    return _create_http_client(
        base_url=base_url,
        insecure=insecure,
        organization_id=organization_id,
        credential_store=credential_store,
        login_flow=login_flow,
    )
