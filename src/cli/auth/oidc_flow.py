"""
OIDC browser-based login flow using a local callback server.
"""

import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Callable, Optional

from authlib.integrations.requests_client import OAuth2Session
from rich.console import Console

from cli.auth.credential_store import CredentialStore
from cli.auth.login_page import LOGIN_SUCCESS_HTML
from cli.utils.url_utils import build_oidc_endpoints

_CALLBACK_PORT = 54422
_CALLBACK_HOST = "127.0.0.1"


class _CallbackHandler(BaseHTTPRequestHandler):
    """
    HTTP request handler that captures the OIDC authorization callback.
    """

    def do_GET(self) -> None:
        """
        Handle the GET request from the identity provider redirect.
        """
        self.server.callback_url = f"http://{_CALLBACK_HOST}:{_CALLBACK_PORT}{self.path}"
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(LOGIN_SUCCESS_HTML)

    def log_message(self, format: str, *args: object) -> None:
        """
        Suppress default HTTP server logging.
        """


class CallbackServer:
    """
    A local HTTP server that listens for the OIDC authorization callback.
    """

    def __init__(self) -> None:
        """
        Initialize the callback server on the fixed callback port.
        """
        self._server = HTTPServer((_CALLBACK_HOST, _CALLBACK_PORT), _CallbackHandler)
        self._server.callback_url: Optional[str] = None

    @property
    def redirect_uri(self) -> str:
        """
        Return the redirect URI that the identity provider should redirect to.
        """
        return f"http://{_CALLBACK_HOST}:{_CALLBACK_PORT}/callback"

    def wait_for_callback(self, timeout: int = 120) -> str:
        """
        Block until the authorization callback is received.

        Returns the full callback URL including query parameters.
        """
        self._server.timeout = timeout
        self._server.handle_request()
        if self._server.callback_url is None:
            raise TimeoutError("Timed out waiting for the authorization callback.")
        return self._server.callback_url

    def shutdown(self) -> None:
        """
        Shut down the callback server.
        """
        threading.Thread(target=self._server.shutdown, daemon=True).start()


class OidcLoginFlow:
    """
    Orchestrates the OIDC browser-based login flow.
    """

    def __init__(
        self,
        identity_base_url: str,
        organization_id: str,
        credential_store: CredentialStore,
        browser_opener: Callable[[str], None] = webbrowser.open,
        callback_server_factory: Callable[[], CallbackServer] = CallbackServer,
        session_factory: Callable[..., OAuth2Session] = OAuth2Session,
        console: Optional[Console] = None,
        insecure: bool = False,
    ) -> None:
        """
        Initialize the OIDC login flow.

        Args:
            identity_base_url: The base URL for the identity provider.
            organization_id: The organization (Keycloak realm) to authenticate against.
            credential_store: Where to persist the resulting tokens.
            browser_opener: Callable to open a URL in the browser.
            callback_server_factory: Factory for creating the local callback server.
            session_factory: Factory for creating an OAuth2Session.
            console: Rich console for output (defaults to a new Console).
            insecure: If True, disable SSL certificate verification on token requests.
        """
        self._identity_base_url = identity_base_url
        self._organization_id = organization_id
        self._credential_store = credential_store
        self._browser_opener = browser_opener
        self._callback_server_factory = callback_server_factory
        self._session_factory = session_factory
        self._console = console or Console()
        self._insecure = insecure

    def login(self) -> dict:
        """
        Run the full OIDC login flow.

        Opens a browser for the user to authenticate, waits for the callback,
        exchanges the authorization code for tokens, saves them, and returns
        the token dict.
        """
        endpoints = build_oidc_endpoints(
            identity_base_url=self._identity_base_url,
            organization_id=self._organization_id,
        )

        callback_server = self._callback_server_factory()
        try:
            return self._perform_login(
                endpoints=endpoints,
                callback_server=callback_server,
            )
        finally:
            callback_server.shutdown()

    def _perform_login(self, endpoints: dict, callback_server: CallbackServer) -> dict:
        """
        Perform the login steps: create session, open browser, exchange code, save token.
        """
        session = self._session_factory(
            client_id="hiverge",
            redirect_uri=callback_server.redirect_uri,
            scope="openid",
            code_challenge_method="S256",
        )
        if self._insecure:
            session.verify = False

        authorization_url, _ = session.create_authorization_url(
            endpoints["authorization_endpoint"]
        )

        self._open_browser(url=authorization_url)

        callback_url = callback_server.wait_for_callback()

        token = session.fetch_token(
            url=endpoints["token_endpoint"],
            authorization_response=callback_url,
        )

        self._credential_store.save_token(
            organization_id=self._organization_id,
            token=token,
        )

        return token

    def _open_browser(self, url: str) -> None:
        """
        Attempt to open the authorization URL in the user's browser.
        Falls back to printing the URL if the browser cannot be opened.
        """
        try:
            self._browser_opener(url)
        except Exception:
            self._console.print(
                "[yellow]Please open the following URL in your browser:[/yellow]"
            )
            self._console.print(url)
