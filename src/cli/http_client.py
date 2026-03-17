"""
HTTP client for communicating with the Hive backend server.
"""

import os
from typing import Any, Callable, Dict, Optional

import requests
from authlib.integrations.requests_client import OAuth2Session
from rich.console import Console

from cli.auth.credential_store import CredentialStore
from cli.auth.oidc_flow import OidcLoginFlow
from cli.utils.url_utils import build_oidc_endpoints, derive_identity_base_url

console = Console()


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
        *,
        base_url: Optional[str] = None,
        session: Optional[requests.Session] = None,
        on_auth_failure: Optional[Callable[[], requests.Session]] = None,
        insecure: bool = False,
    ) -> None:
        """
        Initialize the HTTP client.

        Args:
            base_url: Base URL of the backend server (defaults to env var HIVE_API_ENDPOINT).
            session: Pre-configured HTTP session for making requests.
            on_auth_failure: Optional callback invoked on 401 responses. Should attempt
                re-authentication and return a new session. If the callback itself fails
                or is not provided, an AuthenticationError is raised.
            insecure: If True, disable SSL certificate verification on all requests.
        """
        self.base_url = (
            base_url
            or os.getenv("HIVE_API_ENDPOINT", "https://platform.hiverge.ai/api/v1")
        ).rstrip("/")
        self._session = session or requests.Session()
        self._on_auth_failure = on_auth_failure
        self._insecure = insecure
        if insecure:
            self._session.verify = False

    def _get_headers(self) -> Dict[str, str]:
        """
        Get common headers for all requests.
        """
        return {"Content-Type": "application/json"}

    def _request(
        self,
        *,
        method: str,
        url: str,
        headers: Dict[str, str],
        json: Optional[Dict[str, Any]] = None,
    ) -> requests.Response:
        """
        Make an HTTP request, automatically retrying once on 401 if an
        on_auth_failure callback is configured.
        """
        response = getattr(self._session, method)(
            url, headers=headers, json=json, timeout=30
        )
        if response.status_code == 401 and self._on_auth_failure is not None:
            try:
                self._session = self._on_auth_failure()
                if self._insecure:
                    self._session.verify = False
            except Exception as e:
                raise AuthenticationError(
                    "Your credentials have expired. Please run 'hive login' to re-authenticate."
                ) from e
            response = getattr(self._session, method)(
                url, headers=headers, json=json, timeout=30
            )
            if response.status_code == 401:
                raise AuthenticationError(
                    "Your credentials have expired. Please run 'hive login' to re-authenticate."
                )
        elif response.status_code == 401:
            raise AuthenticationError(
                "Your credentials have expired. Please run 'hive login' to re-authenticate."
            )
        return response

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


def create_http_client(
    *,
    base_url: str,
    no_auth: bool,
    insecure: bool = False,
    organization_id: Optional[str] = None,
    credential_store: Optional[CredentialStore] = None,
    login_flow: Optional[OidcLoginFlow] = None,
) -> HttpClient:
    """
    Create an HttpClient with the appropriate authentication configuration.

    Args:
        base_url: Base URL of the backend server.
        no_auth: If True, skip authentication entirely.
        insecure: If True, disable SSL certificate verification.
        organization_id: The organization ID for token storage.
        credential_store: The credential store for loading/saving tokens.
        login_flow: Optional OIDC login flow for automatic re-authentication.

    Returns:
        A configured HttpClient instance.
    """
    if no_auth:
        return HttpClient(base_url=base_url, session=requests.Session(), insecure=insecure)

    on_auth_failure = None
    if login_flow is not None:
        def _re_authenticate() -> requests.Session:
            """
            Attempt to re-authenticate via the OIDC login flow and return
            a new session with the fresh token.
            """
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

        on_auth_failure = _re_authenticate

    # Try to load an existing token
    session = None
    if credential_store is not None and organization_id is not None:
        token = credential_store.load_token(organization_id=organization_id)
        if token is not None:
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
        elif on_auth_failure is not None:
            # No stored token — attempt auto-login
            try:
                session = on_auth_failure()
            except Exception as e:
                raise AuthenticationError(
                    "Login failed. Please run 'hive login' to authenticate."
                ) from e

    return HttpClient(
        base_url=base_url,
        session=session or requests.Session(),
        on_auth_failure=on_auth_failure,
        insecure=insecure,
    )
