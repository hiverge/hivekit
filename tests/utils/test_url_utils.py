"""
Tests for the URL utility functions.
"""

import os
from unittest.mock import patch

import pytest

from cli.utils.url_utils import build_oidc_endpoints, derive_identity_base_url, get_api_endpoint


class TestGetApiEndpoint:
    """
    Tests for the `get_api_endpoint` function.
    """

    def test_returns_default_when_env_not_set(self) -> None:
        """
        Test that the default API endpoint is returned when the environment
        variable is not set.
        """
        # given
        with patch.dict(os.environ, {}, clear=True):
            # when
            result = get_api_endpoint()

        # then
        assert result == "https://platform.hiverge.ai/api/v1"

    @patch.dict(os.environ, {"HIVE_API_ENDPOINT": "https://custom.example.com/api"})
    def test_returns_env_variable_when_set(self) -> None:
        """
        Test that the HIVE_API_ENDPOINT environment variable is used when set.
        """
        # when
        result = get_api_endpoint()

        # then
        assert result == "https://custom.example.com/api"


class TestDeriveIdentityBaseUrl:
    """
    Tests for the `derive_identity_base_url` function.
    """

    @pytest.mark.parametrize(
        "api_endpoint, expected",
        [
            pytest.param(
                "https://platform.hiverge.ai/api/v1",
                "https://platform.hiverge.ai/identity",
                id="Standard platform URL",
            ),
            pytest.param(
                "https://platform.hiverge.ai/api/v1/",
                "https://platform.hiverge.ai/identity",
                id="Trailing slash",
            ),
            pytest.param(
                "https://custom.example.com/api/v1",
                "https://custom.example.com/identity",
                id="Custom domain",
            ),
            pytest.param(
                "http://localhost:8080/api/v1",
                "http://localhost:8080/identity",
                id="Localhost with port",
            ),
            pytest.param(
                "https://platform.hiverge.ai/some/other/path",
                "https://platform.hiverge.ai/identity",
                id="Arbitrary path is stripped",
            ),
            pytest.param(
                "https://platform.hiverge.ai",
                "https://platform.hiverge.ai/identity",
                id="No path",
            ),
        ],
    )
    def test_derives_identity_url(self, api_endpoint: str, expected: str) -> None:
        """
        Test that the identity base URL is correctly derived from the API endpoint.
        """
        # when
        result = derive_identity_base_url(api_endpoint=api_endpoint)

        # then
        assert result == expected


class TestBuildOidcEndpoints:
    """
    Tests for the `build_oidc_endpoints` function.
    """

    def test_builds_correct_endpoints(self) -> None:
        """
        Test that the OIDC endpoints are correctly constructed from the identity
        base URL and organization ID.
        """
        # given
        identity_base_url = "https://platform.hiverge.ai/identity"
        organization_id = "my-org"

        # when
        endpoints = build_oidc_endpoints(
            identity_base_url=identity_base_url,
            organization_id=organization_id,
        )

        # then
        assert endpoints == {
            "authorization_endpoint": "https://platform.hiverge.ai/identity/realms/my-org/"
                                      "protocol/openid-connect/auth",
            "token_endpoint": "https://platform.hiverge.ai/identity/realms/my-org/"
                              "protocol/openid-connect/token",
            "userinfo_endpoint": "https://platform.hiverge.ai/identity/realms/my-org/"
                                 "protocol/openid-connect/userinfo",
        }

    def test_builds_endpoints_with_trailing_slash(self) -> None:
        """
        Test that a trailing slash on the identity base URL is handled correctly.
        """
        # given
        identity_base_url = "https://platform.hiverge.ai/identity/"
        organization_id = "other-org"

        # when
        endpoints = build_oidc_endpoints(
            identity_base_url=identity_base_url,
            organization_id=organization_id,
        )

        # then
        assert endpoints == {
            "authorization_endpoint": "https://platform.hiverge.ai/identity/realms/other-org/"
                                      "protocol/openid-connect/auth",
            "token_endpoint": "https://platform.hiverge.ai/identity/realms/other-org/"
                              "protocol/openid-connect/token",
            "userinfo_endpoint": "https://platform.hiverge.ai/identity/realms/other-org/"
                                 "protocol/openid-connect/userinfo",
        }
