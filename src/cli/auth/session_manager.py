"""
Manages OAuth2 sessions for OIDC authentication.

Handles creating sessions from stored tokens, triggering login flows,
and re-authenticating when tokens expire.
"""

import logging
import os
from typing import Any, Dict

from authlib.integrations.requests_client import OAuth2Session

from cli.auth.auth_utils import get_machine_id
from cli.auth.credential_store import CredentialStore, create_credential_store
from cli.auth.oidc_flow import OidcLoginFlow
from cli.utils.config_paths import get_config_dir
from cli.utils.url_utils import build_oidc_endpoints, derive_identity_base_url

logger = logging.getLogger("hivekit")

_OIDC_CLIENT_ID = "hiverge"


class OidcSessionManager:
    """
    Creates and refreshes OAuth2 sessions using OIDC.
    """

    def __init__(
        self,
        organization_id: str,
        credential_store: CredentialStore,
        login_flow: OidcLoginFlow,
        token_endpoint: str,
        insecure: bool = False,
    ) -> None:
        """
        Initialize the session manager.

        Args:
            organization_id: The organization (Keycloak realm) to authenticate against.
            credential_store: Where to load and persist tokens.
            login_flow: The OIDC login flow for interactive authentication.
            token_endpoint: The OIDC token endpoint URL.
            insecure: If True, disable SSL certificate verification on all requests.
        """
        self._organization_id = organization_id
        self._credential_store = credential_store
        self._login_flow = login_flow
        self._token_endpoint = token_endpoint
        self._insecure = insecure

    def create_session(self) -> OAuth2Session:
        """
        Creates an OAuth2Session from a stored token, or initiates the login flow
        if no stored token is available.
        """
        token = self._credential_store.load_token(organization_id=self._organization_id)
        if token is None:
            logger.info(
                f"No stored token available for organization '{self._organization_id}'. "
                f"Login is required."
            )
            return self.login()
        else:
            logger.info(f"Loaded stored token for organization '{self._organization_id}'.")
            return self._build_session(token=token)

    def login(self) -> OAuth2Session:
        """
        Run the interactive OIDC login flow and return a new session.

        Returns:
            A configured OAuth2Session with the fresh token.
        """
        logger.info(f"Starting OIDC login flow for organization '{self._organization_id}'.")
        token = self._login_flow.login()
        self._on_token_update(
            new_token=token,
        )
        return self._build_session(token=token)

    def _build_session(self, token: Dict[str, Any]) -> OAuth2Session:
        """
        Build an OAuth2Session with the given token, configured to persist
        refreshed tokens to the credential store.
        """
        session = OAuth2Session(
            client_id=_OIDC_CLIENT_ID,
            token=token,
            token_endpoint=self._token_endpoint,
            update_token=self._on_token_update,
        )
        if self._insecure:
            session.verify = False
        return session

    def _on_token_update(self, new_token: Dict[str, Any], **kwargs: object) -> None:
        """
        Callback invoked by authlib when a token is refreshed.
        """
        self._credential_store.save_token(
            organization_id=self._organization_id,
            token=new_token,
        )


def create_session_manager(
    organization_id: str,
    base_url: str,
    insecure: bool = False,
) -> OidcSessionManager:
    """
    Create an OidcSessionManager with all required dependencies.

    Builds the credential store, login flow, and OIDC endpoints from the
    given parameters.

    Args:
        organization_id: The organization (Keycloak realm) to authenticate against.
        base_url: The API base URL, used to derive the identity provider URL.
        insecure: If True, disable SSL certificate verification.

    Returns:
        A configured OidcSessionManager.
    """
    identity_base_url = derive_identity_base_url(api_endpoint=base_url)
    credential_store = create_credential_store(
        clients_dir=os.path.join(get_config_dir(), "clients"),
        machine_id_func=get_machine_id,
    )
    login_flow = OidcLoginFlow(
        identity_base_url=identity_base_url,
        organization_id=organization_id,
        insecure=insecure,
    )
    endpoints = build_oidc_endpoints(
        identity_base_url=identity_base_url,
        organization_id=organization_id,
    )
    return OidcSessionManager(
        organization_id=organization_id,
        credential_store=credential_store,
        login_flow=login_flow,
        token_endpoint=endpoints["token_endpoint"],
        insecure=insecure,
    )
