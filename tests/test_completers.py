"""
Unit tests for argcomplete completer functions.
"""

from unittest.mock import MagicMock, patch

from cli.completers import config_file_completer, experiment_completer


class TestExperimentCompleter:
    """Tests for experiment_completer function."""

    @patch("cli.completers.create_http_client")
    @patch("cli.completers.load_config")
    def test_experiment_completer_success(self, mock_load_config, mock_create_client):
        """Test experiment_completer successfully fetches and returns experiment names."""
        # Setup mock client
        mock_config = MagicMock()
        mock_config.organization_id = "my-org"
        mock_load_config.return_value = mock_config

        mock_client = MagicMock()
        mock_create_client.return_value = mock_client

        # Mock API response
        mock_client.list_experiments.return_value = {
            "experiments": [
                {"metadata": {"name": "exp-1"}},
                {"metadata": {"name": "exp-2"}},
                {"metadata": {"name": "exp-3"}},
            ]
        }

        # Call completer
        result = experiment_completer("")

        # Verify results
        assert result == ["exp-1", "exp-2", "exp-3"]
        mock_client.list_experiments.assert_called_once()
        mock_create_client.assert_called_once_with(organization_id="my-org")

    @patch("cli.completers.create_http_client")
    @patch("cli.completers.load_config")
    def test_experiment_completer_with_prefix(self, mock_load_config, mock_create_client):
        """Test experiment_completer filters by prefix."""
        # Setup mock client
        mock_config = MagicMock()
        mock_config.organization_id = "my-org"
        mock_load_config.return_value = mock_config

        mock_client = MagicMock()
        mock_create_client.return_value = mock_client

        mock_client.list_experiments.return_value = {
            "experiments": [
                {"metadata": {"name": "exp-1"}},
                {"metadata": {"name": "exp-2"}},
                {"metadata": {"name": "test-1"}},
            ]
        }

        # Call completer with prefix
        result = experiment_completer("exp")

        # Should only return experiments starting with "exp"
        assert result == ["exp-1", "exp-2"]

    @patch("cli.completers.create_http_client")
    @patch("cli.completers.load_config")
    def test_experiment_completer_api_error(self, mock_load_config, mock_create_client):
        """Test experiment_completer returns empty list on API error."""
        # Setup mock client
        mock_config = MagicMock()
        mock_config.organization_id = "my-org"
        mock_load_config.return_value = mock_config

        mock_client = MagicMock()
        mock_create_client.return_value = mock_client

        # Simulate API error
        mock_client.list_experiments.side_effect = Exception("API error")

        # Call completer
        result = experiment_completer("")

        # Should return empty list on error
        assert result == []

    @patch("cli.completers.create_http_client")
    @patch("cli.completers.load_config")
    def test_experiment_completer_empty_response(self, mock_load_config, mock_create_client):
        """Test experiment_completer handles empty API response."""
        # Setup mock client
        mock_config = MagicMock()
        mock_config.organization_id = "my-org"
        mock_load_config.return_value = mock_config

        mock_client = MagicMock()
        mock_create_client.return_value = mock_client

        # Mock empty response
        mock_client.list_experiments.return_value = {"experiments": []}

        # Call completer
        result = experiment_completer("")

        # Should return empty list
        assert result == []

    @patch("cli.completers.create_http_client")
    @patch("cli.completers.load_config")
    def test_experiment_completer_missing_metadata(self, mock_load_config, mock_create_client):
        """Test experiment_completer handles experiments with missing metadata."""
        # Setup mock client
        mock_config = MagicMock()
        mock_config.organization_id = "my-org"
        mock_load_config.return_value = mock_config

        mock_client = MagicMock()
        mock_create_client.return_value = mock_client

        # Mock response with missing/malformed data
        mock_client.list_experiments.return_value = {
            "experiments": [
                {"metadata": {"name": "exp-1"}},
                {"metadata": {}},  # Missing name
                {},  # Missing metadata
                {"metadata": {"name": "exp-2"}},
            ]
        }

        # Call completer
        result = experiment_completer("")

        # Should only return valid experiment names
        assert result == ["exp-1", "exp-2"]


class TestConfigFileCompleter:
    """Tests for config_file_completer function."""

    @patch("cli.completers.FilesCompleter")
    def test_config_file_completer(self, mock_files_completer):
        """Test config_file_completer delegates to FilesCompleter."""
        # Setup mock
        mock_completer_instance = MagicMock()
        mock_completer_instance.return_value = ["/path/to/file1.yaml", "/path/to/file2.yaml"]
        mock_files_completer.return_value = mock_completer_instance

        # Call completer
        result = config_file_completer("~/.hive/")

        # Verify FilesCompleter was used
        mock_files_completer.assert_called_once()
        mock_completer_instance.assert_called_once_with("~/.hive/")
        assert result == ["/path/to/file1.yaml", "/path/to/file2.yaml"]

    @patch("cli.completers.FilesCompleter")
    def test_config_file_completer_error(self, mock_files_completer):
        """Test config_file_completer returns empty list on error."""
        # Setup mock to raise exception
        mock_files_completer.side_effect = Exception("Completer error")

        # Call completer
        result = config_file_completer("~/.hive/")

        # Should return empty list on error
        assert result == []
