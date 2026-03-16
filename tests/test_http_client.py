"""
Unit tests for HttpClient class.
"""

import os
from unittest.mock import MagicMock, mock_open, patch

import pytest
import requests

from cli.http_client import HttpClient


class TestHttpClientInit:
    """Tests for HttpClient initialization."""

    @patch("cli.http_client.os.path.exists")
    @patch("builtins.open", new_callable=mock_open, read_data="test-token")
    def test_init_with_token_file(self, mock_file, mock_exists):
        """Test initialization when token file exists."""
        mock_exists.return_value = True

        client = HttpClient()

        assert client.auth_token == "test-token"
        assert client.base_url == "http://localhost:8080/api/v1"
        assert client.token_path == os.path.expandvars("$HOME/.hive/token")

    @patch("cli.http_client.os.path.exists")
    def test_init_without_token_file(self, mock_exists):
        """Test initialization when token file doesn't exist."""
        mock_exists.return_value = False

        client = HttpClient()

        assert client.auth_token == ""
        assert isinstance(client.session, requests.Session)

    @patch("cli.http_client.os.path.exists")
    @patch("builtins.open", new_callable=mock_open, read_data="test-token")
    def test_init_with_custom_base_url(self, mock_file, mock_exists):
        """Test initialization with custom base URL."""
        mock_exists.return_value = True

        client = HttpClient(base_url="https://custom-server.com/api")

        assert client.base_url == "https://custom-server.com/api"

    @patch("cli.http_client.os.path.exists")
    @patch("builtins.open", new_callable=mock_open, read_data="test-token")
    def test_init_strips_trailing_slash(self, mock_file, mock_exists):
        """Test that trailing slash is removed from base URL."""
        mock_exists.return_value = True

        client = HttpClient(base_url="https://server.com/api/")

        assert client.base_url == "https://server.com/api"

    @patch("cli.http_client.os.path.exists")
    @patch.dict(os.environ, {"HIVE_API_ENDPOINT": "https://env-server.com"})
    def test_init_uses_env_variable(self, mock_exists):
        """Test that HIVE_API_ENDPOINT environment variable is used."""
        mock_exists.return_value = False

        client = HttpClient()

        assert client.base_url == "https://env-server.com"


class TestHttpClientCreateExperiment:
    """Tests for create_experiment method."""

    @patch("cli.http_client.os.path.exists")
    @patch("builtins.open", new_callable=mock_open, read_data="token")
    def test_create_experiment_success(self, mock_file, mock_exists):
        """Test successful experiment creation."""
        mock_exists.return_value = True
        client = HttpClient()

        mock_response = MagicMock()
        mock_response.json.return_value = {"metadata": {"name": "test-exp"}}
        client.session.post = MagicMock(return_value=mock_response)

        experiment_data = {"metadata": {"name": "test-exp"}}
        result = client.create_experiment(experiment_data)

        assert result == {"metadata": {"name": "test-exp"}}
        client.session.post.assert_called_once()

    @patch("cli.http_client.os.path.exists")
    @patch("builtins.open", new_callable=mock_open, read_data="token")
    def test_create_experiment_http_error_with_json(self, mock_file, mock_exists):
        """Test create_experiment handles HTTP error with JSON response."""
        mock_exists.return_value = True
        client = HttpClient()

        mock_response = MagicMock()
        mock_response.json.return_value = {"error": "Bad request"}
        http_error = requests.exceptions.HTTPError()
        http_error.response = mock_response
        client.session.post = MagicMock(side_effect=http_error)

        with pytest.raises(Exception, match="Failed to create experiment: Bad request"):
            client.create_experiment({"metadata": {"name": "test"}})

    @patch("cli.http_client.os.path.exists")
    @patch("builtins.open", new_callable=mock_open, read_data="token")
    def test_create_experiment_http_error_with_text(self, mock_file, mock_exists):
        """Test create_experiment handles HTTP error with text response."""
        mock_exists.return_value = True
        client = HttpClient()

        mock_response = MagicMock()
        mock_response.json.side_effect = ValueError("Not JSON")
        mock_response.text = "Server error"
        http_error = requests.exceptions.HTTPError()
        http_error.response = mock_response
        client.session.post = MagicMock(side_effect=http_error)

        with pytest.raises(Exception, match="Failed to create experiment: Server error"):
            client.create_experiment({"metadata": {"name": "test"}})

    @patch("cli.http_client.os.path.exists")
    @patch("builtins.open", new_callable=mock_open, read_data="token")
    def test_create_experiment_connection_error(self, mock_file, mock_exists):
        """Test create_experiment handles connection errors."""
        mock_exists.return_value = True
        client = HttpClient()

        client.session.post = MagicMock(
            side_effect=requests.exceptions.ConnectionError("Connection failed")
        )

        with pytest.raises(Exception, match="Failed to connect to backend server"):
            client.create_experiment({"metadata": {"name": "test"}})


class TestHttpClientGetExperiment:
    """Tests for get_experiment method."""

    @patch("cli.http_client.os.path.exists")
    @patch("builtins.open", new_callable=mock_open, read_data="token")
    def test_get_experiment_success(self, mock_file, mock_exists):
        """Test successful get experiment."""
        mock_exists.return_value = True
        client = HttpClient()

        mock_response = MagicMock()
        mock_response.json.return_value = {"metadata": {"name": "test-exp"}}
        client.session.get = MagicMock(return_value=mock_response)

        result = client.get_experiment("test-exp")

        assert result == {"metadata": {"name": "test-exp"}}
        client.session.get.assert_called_once()

    @patch("cli.http_client.os.path.exists")
    @patch("builtins.open", new_callable=mock_open, read_data="token")
    def test_get_experiment_error(self, mock_file, mock_exists):
        """Test get_experiment handles errors."""
        mock_exists.return_value = True
        client = HttpClient()

        client.session.get = MagicMock(side_effect=requests.exceptions.RequestException("Error"))

        with pytest.raises(Exception, match="Failed to get experiment"):
            client.get_experiment("test-exp")


class TestHttpClientListExperiments:
    """Tests for list_experiments method."""

    @patch("cli.http_client.os.path.exists")
    @patch("builtins.open", new_callable=mock_open, read_data="token")
    def test_list_experiments_success(self, mock_file, mock_exists):
        """Test successful list experiments."""
        mock_exists.return_value = True
        client = HttpClient()

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "experiments": [{"metadata": {"name": "exp1"}}, {"metadata": {"name": "exp2"}}]
        }
        client.session.get = MagicMock(return_value=mock_response)

        result = client.list_experiments()

        assert len(result["experiments"]) == 2
        client.session.get.assert_called_once()

    @patch("cli.http_client.os.path.exists")
    @patch("builtins.open", new_callable=mock_open, read_data="token")
    def test_list_experiments_error(self, mock_file, mock_exists):
        """Test list_experiments handles errors."""
        mock_exists.return_value = True
        client = HttpClient()

        client.session.get = MagicMock(side_effect=requests.exceptions.RequestException("Error"))

        with pytest.raises(Exception, match="Failed to list experiments"):
            client.list_experiments()


class TestHttpClientDeleteExperiment:
    """Tests for delete_experiment method."""

    @patch("cli.http_client.os.path.exists")
    @patch("builtins.open", new_callable=mock_open, read_data="token")
    def test_delete_experiment_success(self, mock_file, mock_exists):
        """Test successful delete experiment."""
        mock_exists.return_value = True
        client = HttpClient()

        mock_response = MagicMock()
        mock_response.json.return_value = {"message": "Deleted"}
        client.session.delete = MagicMock(return_value=mock_response)

        result = client.delete_experiment("test-exp")

        assert result == {"message": "Deleted"}
        client.session.delete.assert_called_once()

    @patch("cli.http_client.os.path.exists")
    @patch("builtins.open", new_callable=mock_open, read_data="token")
    def test_delete_experiment_error(self, mock_file, mock_exists):
        """Test delete_experiment handles errors."""
        mock_exists.return_value = True
        client = HttpClient()

        client.session.delete = MagicMock(side_effect=requests.exceptions.RequestException("Error"))

        with pytest.raises(Exception, match="Failed to delete experiment"):
            client.delete_experiment("test-exp")
