"""
Utility functions for deriving OIDC-related URLs and the API endpoint.
"""

import os
from urllib.parse import urlparse

_DEFAULT_API_ENDPOINT = "https://platform.hiverge.ai/api/v1"


def get_api_endpoint() -> str:
    """
    Return the API endpoint from the HIVE_API_ENDPOINT environment variable,
    or the default if not set.
    """
    return os.getenv("HIVE_API_ENDPOINT", _DEFAULT_API_ENDPOINT)


def derive_identity_base_url(api_endpoint: str) -> str:
    """
    Derive the identity provider base URL from the API endpoint.

    Strips the entire path from the URL and appends `/identity`.
    For example, `https://platform.hiverge.ai/api/v1` becomes
    `https://platform.hiverge.ai/identity`.
    """
    parsed = urlparse(api_endpoint)
    return f"{parsed.scheme}://{parsed.netloc}/identity"


def build_oidc_endpoints(identity_base_url: str, organization_id: str) -> dict[str, str]:
    """
    Build the OIDC endpoint URLs for a given organization.

    Returns a dict with `authorization_endpoint`, `token_endpoint`, and
    `userinfo_endpoint` keys.
    """
    base = identity_base_url.rstrip("/")
    realm_base = f"{base}/realms/{organization_id}/protocol/openid-connect"
    return {
        "authorization_endpoint": f"{realm_base}/auth",
        "token_endpoint": f"{realm_base}/token",
        "userinfo_endpoint": f"{realm_base}/userinfo",
    }
