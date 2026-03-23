"""
Unit tests for argcomplete completer functions.
"""

from unittest.mock import MagicMock, patch

from cli.completers import config_file_completer, experiment_completer


class TestExperimentCompleter:
    """
    Tests for the `experiment_completer` function.
    """

    @patch("cli.completers.build_http_client")
    def test_experiment_completer_success(self, mock_create_client):
        """
        Test that experiment_completer successfully fetches and returns experiment names.
        """
        # given
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client
        mock_client.list_experiments.return_value = {
            "experiments": [
                {"metadata": {"name": "exp-1"}},
                {"metadata": {"name": "exp-2"}},
                {"metadata": {"name": "exp-3"}},
            ]
        }

        # when
        result = experiment_completer("")

        # then
        assert result == ["exp-1", "exp-2", "exp-3"]
        mock_create_client.assert_called_once()
        mock_client.list_experiments.assert_called_once()

    @patch("cli.completers.build_http_client")
    def test_experiment_completer_with_prefix(self, mock_create_client):
        """
        Test that experiment_completer filters results by prefix.
        """
        # given
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client
        mock_client.list_experiments.return_value = {
            "experiments": [
                {"metadata": {"name": "exp-1"}},
                {"metadata": {"name": "exp-2"}},
                {"metadata": {"name": "test-1"}},
            ]
        }

        # when
        result = experiment_completer("exp")

        # then
        assert result == ["exp-1", "exp-2"]

    @patch("cli.completers.build_http_client")
    def test_experiment_completer_api_error(self, mock_create_client):
        """
        Test that experiment_completer returns an empty list on API error.
        """
        # given
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client
        mock_client.list_experiments.side_effect = Exception("API error")

        # when
        result = experiment_completer("")

        # then
        assert result == []

    @patch("cli.completers.build_http_client")
    def test_experiment_completer_empty_response(self, mock_create_client):
        """
        Test that experiment_completer handles an empty API response.
        """
        # given
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client
        mock_client.list_experiments.return_value = {"experiments": []}

        # when
        result = experiment_completer("")

        # then
        assert result == []

    @patch("cli.completers.build_http_client")
    def test_experiment_completer_missing_metadata(self, mock_create_client):
        """
        Test that experiment_completer handles experiments with missing metadata.
        """
        # given
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client
        mock_client.list_experiments.return_value = {
            "experiments": [
                {"metadata": {"name": "exp-1"}},
                {"metadata": {}},
                {},
                {"metadata": {"name": "exp-2"}},
            ]
        }

        # when
        result = experiment_completer("")

        # then
        assert result == ["exp-1", "exp-2"]


class TestConfigFileCompleter:
    """
    Tests for the `config_file_completer` function.
    """

    @patch("cli.completers.FilesCompleter")
    def test_config_file_completer(self, mock_files_completer):
        """
        Test that config_file_completer delegates to FilesCompleter.
        """
        # given
        mock_completer_instance = MagicMock()
        mock_completer_instance.return_value = ["/path/to/file1.yaml", "/path/to/file2.yaml"]
        mock_files_completer.return_value = mock_completer_instance

        # when
        result = config_file_completer("~/.hive/")

        # then
        mock_files_completer.assert_called_once()
        mock_completer_instance.assert_called_once_with("~/.hive/")
        assert result == ["/path/to/file1.yaml", "/path/to/file2.yaml"]

    @patch("cli.completers.FilesCompleter")
    def test_config_file_completer_error(self, mock_files_completer):
        """
        Test that config_file_completer returns an empty list on error.
        """
        # given
        mock_files_completer.side_effect = Exception("Completer error")

        # when
        result = config_file_completer("~/.hive/")

        # then
        assert result == []
