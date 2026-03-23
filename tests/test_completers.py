"""
Unit tests for argcomplete completer functions.
"""

from typing import List
from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture

from cli.completers import config_file_completer, experiment_completer

_ALL_EXPERIMENTS = [
    {"metadata": {"name": "exp-1"}},
    {"metadata": {"name": "exp-2"}},
    {"metadata": {"name": "test-1"}},
]


class TestExperimentCompleter:
    """
    Tests for the `experiment_completer` function.
    """

    @pytest.mark.parametrize(
        "experiments, prefix, expected",
        [
            pytest.param(
                _ALL_EXPERIMENTS,
                "",
                ["exp-1", "exp-2", "test-1"],
                id="No prefix returns all names",
            ),
            pytest.param(
                _ALL_EXPERIMENTS,
                "exp",
                ["exp-1", "exp-2"],
                id="Prefix filters matching names",
            ),
            pytest.param(
                {"experiments": []},
                "",
                [],
                id="Empty response returns empty list",
            ),
            pytest.param(
                [
                    {"metadata": {"name": "exp-1"}},
                    {"metadata": {}},
                    {},
                    {"metadata": {"name": "exp-2"}},
                ],
                "",
                ["exp-1", "exp-2"],
                id="Missing metadata is skipped",
            ),
        ],
    )
    def test_returns_matching_experiment_names(
        self,
        mocker: MockerFixture,
        experiments: list,
        prefix: str,
        expected: List[str],
    ) -> None:
        """
        Test that experiment_completer returns the correct experiment names
        for various inputs.
        """
        # given
        mock_load_config = mocker.patch("cli.completers.load_config")
        mock_config = MagicMock()
        mock_config.organization_id = "my-org"
        mock_load_config.return_value = mock_config

        mock_build_client = mocker.patch("cli.completers.create_http_client")
        mock_client = MagicMock()
        mock_build_client.return_value = mock_client
        if isinstance(experiments, dict):
            mock_client.list_experiments.return_value = experiments
        else:
            mock_client.list_experiments.return_value = {"experiments": experiments}

        # when
        result = experiment_completer(prefix)

        # then
        assert result == expected
        mock_build_client.assert_called_once_with(organization_id="my-org")

    def test_returns_empty_list_on_api_error(
        self, mocker: MockerFixture,
    ) -> None:
        """
        Test that experiment_completer returns an empty list on API error.
        """
        # given
        mock_load_config = mocker.patch("cli.completers.load_config")
        mock_config = MagicMock()
        mock_config.organization_id = "my-org"
        mock_load_config.return_value = mock_config

        mock_build_client = mocker.patch("cli.completers.create_http_client")
        mock_client = MagicMock()
        mock_build_client.return_value = mock_client
        mock_client.list_experiments.side_effect = Exception("API error")

        # when
        result = experiment_completer("")

        # then
        assert result == []


class TestConfigFileCompleter:
    """
    Tests for the `config_file_completer` function.
    """

    def test_delegates_to_files_completer(self, mocker: MockerFixture) -> None:
        """
        Test that config_file_completer delegates to FilesCompleter.
        """
        # given
        mock_files_completer = mocker.patch("cli.completers.FilesCompleter")
        mock_completer_instance = MagicMock()
        mock_completer_instance.return_value = ["/path/to/file1.yaml", "/path/to/file2.yaml"]
        mock_files_completer.return_value = mock_completer_instance

        # when
        result = config_file_completer("~/.hive/")

        # then
        mock_files_completer.assert_called_once()
        mock_completer_instance.assert_called_once_with("~/.hive/")
        assert result == ["/path/to/file1.yaml", "/path/to/file2.yaml"]

    def test_returns_empty_list_on_error(self, mocker: MockerFixture) -> None:
        """
        Test that config_file_completer returns an empty list on error.
        """
        # given
        mock_files_completer = mocker.patch("cli.completers.FilesCompleter")
        mock_files_completer.side_effect = Exception("Completer error")

        # when
        result = config_file_completer("~/.hive/")

        # then
        assert result == []
