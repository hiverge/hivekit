"""
Unit tests for experiment builder functions.
"""

from unittest.mock import patch

import pytest

from cli.config import (
    EnvConfig,
    GCPConfig,
    HiveConfig,
    PortConfig,
    PromptConfig,
    ProviderConfig,
    RepoConfig,
    ResourceConfig,
    RuntimeConfig,
    SandboxConfig,
    ServiceConfig,
)
from cli.experiment import build_experiment_crd, generate_experiment_name


class TestBuildExperimentCRD:
    """Tests for build_experiment_crd function."""

    def test_build_minimal_crd(self):
        """Test building CRD with minimal required config."""
        config = HiveConfig(
            runtime=RuntimeConfig(),
            repo=RepoConfig(
                source="https://github.com/test/repo.git",
                evolve_files_and_ranges="main.py",
            ),
            sandbox=SandboxConfig(),
            provider=ProviderConfig(gcp=GCPConfig()),
        )

        result = build_experiment_crd(config, "test-exp")

        assert result["apiVersion"] == "core.hiverge.io/v1alpha1"
        assert result["kind"] == "Experiment"
        assert result["metadata"]["name"] == "test-exp"
        assert result["spec"]["runtime"]["numAgents"] == 1
        assert result["spec"]["runtime"]["maxRuntimeSeconds"] == -1
        assert result["spec"]["runtime"]["maxIterations"] == -1
        assert result["spec"]["repo"]["source"] == "https://github.com/test/repo.git"
        assert result["spec"]["repo"]["branch"] == "main"
        assert result["spec"]["sandbox"]["timeout"] == 60
        assert result["spec"]["sandbox"]["resources"]["cpu"] == "1"
        assert result["spec"]["sandbox"]["resources"]["memory"] == "2Gi"

    def test_build_crd_with_runtime_config(self):
        """Test building CRD with custom runtime config."""
        config = HiveConfig(
            runtime=RuntimeConfig(
                num_agents=5, max_runtime_seconds=3600, max_iterations=100
            ),
            repo=RepoConfig(
                source="https://github.com/test/repo.git",
                evolve_files_and_ranges="main.py",
            ),
            sandbox=SandboxConfig(),
            provider=ProviderConfig(gcp=GCPConfig()),
        )

        result = build_experiment_crd(config, "test-exp")

        assert result["spec"]["runtime"]["numAgents"] == 5
        assert result["spec"]["runtime"]["maxRuntimeSeconds"] == 3600
        assert result["spec"]["runtime"]["maxIterations"] == 100

    def test_build_crd_with_optional_repo_fields(self):
        """Test building CRD with optional repo fields."""
        config = HiveConfig(
            runtime=RuntimeConfig(),
            repo=RepoConfig(
                source="https://github.com/test/repo.git",
                branch="dev",
                evaluation_script="eval.py",
                evolve_files_and_ranges="main.py",
                include_files_and_ranges="utils.py:1-10",
            ),
            sandbox=SandboxConfig(),
            provider=ProviderConfig(gcp=GCPConfig()),
        )

        result = build_experiment_crd(config, "test-exp")

        assert result["spec"]["repo"]["branch"] == "dev"
        assert result["spec"]["repo"]["evaluationScript"] == "eval.py"
        assert result["spec"]["repo"]["includeFilesAndRanges"] == "utils.py:1-10"

    def test_build_crd_with_sandbox_resources(self):
        """Test building CRD with custom sandbox resources."""
        config = HiveConfig(
            runtime=RuntimeConfig(),
            repo=RepoConfig(
                source="https://github.com/test/repo.git",
                evolve_files_and_ranges="main.py",
            ),
            sandbox=SandboxConfig(
                resources=ResourceConfig(
                    cpu="2",
                    memory="4Gi",
                    accelerators="a100:2",
                    shmsize="2Gi",
                    extended_resources={"nvidia.com/gpu": "1"},
                )
            ),
            provider=ProviderConfig(gcp=GCPConfig()),
        )

        result = build_experiment_crd(config, "test-exp")

        assert result["spec"]["sandbox"]["resources"]["cpu"] == "2"
        assert result["spec"]["sandbox"]["resources"]["memory"] == "4Gi"
        assert result["spec"]["sandbox"]["resources"]["accelerators"] == "a100:2"
        assert result["spec"]["sandbox"]["resources"]["shmsize"] == "2Gi"
        assert result["spec"]["sandbox"]["resources"]["extendedResources"] == {
            "nvidia.com/gpu": "1"
        }

    def test_build_crd_with_sandbox_image(self):
        """Test building CRD with sandbox image configuration."""
        config = HiveConfig(
            runtime=RuntimeConfig(),
            repo=RepoConfig(
                source="https://github.com/test/repo.git",
                evolve_files_and_ranges="main.py",
            ),
            sandbox=SandboxConfig(
                image="custom-image:latest",
            ),
            provider=ProviderConfig(gcp=GCPConfig()),
        )

        result = build_experiment_crd(config, "test-exp")

        assert result["spec"]["sandbox"]["image"] == "custom-image:latest"

    def test_build_crd_with_sandbox_envs(self):
        """Test building CRD with sandbox environment variables."""
        config = HiveConfig(
            runtime=RuntimeConfig(),
            repo=RepoConfig(
                source="https://github.com/test/repo.git",
                evolve_files_and_ranges="main.py",
            ),
            sandbox=SandboxConfig(
                envs=[
                    EnvConfig(name="VAR1", value="value1"),
                    EnvConfig(name="VAR2", value="value2"),
                ]
            ),
            provider=ProviderConfig(gcp=GCPConfig()),
        )

        result = build_experiment_crd(config, "test-exp")

        assert len(result["spec"]["sandbox"]["envs"]) == 2
        assert result["spec"]["sandbox"]["envs"][0] == {"name": "VAR1", "value": "value1"}
        assert result["spec"]["sandbox"]["envs"][1] == {"name": "VAR2", "value": "value2"}

    def test_build_crd_with_preprocessor(self):
        """Test building CRD with preprocessor."""
        config = HiveConfig(
            runtime=RuntimeConfig(),
            repo=RepoConfig(
                source="https://github.com/test/repo.git",
                evolve_files_and_ranges="main.py",
            ),
            sandbox=SandboxConfig(preprocessor="preprocess.py"),
            provider=ProviderConfig(gcp=GCPConfig()),
        )

        result = build_experiment_crd(config, "test-exp")

        assert result["spec"]["sandbox"]["preprocessor"] == "preprocess.py"

    def test_build_crd_with_services(self):
        """Test building CRD with additional services."""
        config = HiveConfig(
            runtime=RuntimeConfig(),
            repo=RepoConfig(
                source="https://github.com/test/repo.git",
                evolve_files_and_ranges="main.py",
            ),
            sandbox=SandboxConfig(
                services=[
                    ServiceConfig(
                        name="redis",
                        image="redis:latest",
                        ports=[PortConfig(port=6379, protocol="TCP")],
                        envs=[EnvConfig(name="REDIS_PASSWORD", value="secret")],
                        command=["redis-server"],
                        args=["--appendonly", "yes"],
                        resources=ResourceConfig(cpu="500m", memory="1Gi"),
                    )
                ]
            ),
            provider=ProviderConfig(gcp=GCPConfig()),
        )

        result = build_experiment_crd(config, "test-exp")

        assert len(result["spec"]["sandbox"]["services"]) == 1
        service = result["spec"]["sandbox"]["services"][0]
        assert service["name"] == "redis"
        assert service["image"] == "redis:latest"
        assert service["ports"] == [{"port": 6379, "protocol": "TCP"}]
        assert service["envs"] == [{"name": "REDIS_PASSWORD", "value": "secret"}]
        assert service["command"] == ["redis-server"]
        assert service["args"] == ["--appendonly", "yes"]
        assert service["resources"]["cpu"] == "500m"
        assert service["resources"]["memory"] == "1Gi"

    def test_build_crd_with_prompt_config(self):
        """Test building CRD with prompt configuration."""
        config = HiveConfig(
            runtime=RuntimeConfig(),
            repo=RepoConfig(
                source="https://github.com/test/repo.git",
                evolve_files_and_ranges="main.py",
            ),
            sandbox=SandboxConfig(),
            prompt=PromptConfig(
                context="Test context",
                ideas=["idea1", "idea2"],
                enable_evolution=True,
            ),
            provider=ProviderConfig(gcp=GCPConfig()),
        )

        result = build_experiment_crd(config, "test-exp")

        assert result["spec"]["prompt"]["context"] == "Test context"
        assert result["spec"]["prompt"]["ideas"] == ["idea1", "idea2"]
        assert result["spec"]["prompt"]["enableEvolution"] is True

    def test_build_crd_with_coordinator_config(self):
        """Test building CRD with coordinator config."""
        config = HiveConfig(
            runtime=RuntimeConfig(),
            repo=RepoConfig(
                source="https://github.com/test/repo.git",
                evolve_files_and_ranges="main.py",
            ),
            sandbox=SandboxConfig(),
            provider=ProviderConfig(gcp=GCPConfig()),
            coordinator_config_name="custom-coordinator",
        )

        result = build_experiment_crd(config, "test-exp")

        assert result["spec"]["coordinatorConfigName"] == "custom-coordinator"

    def test_build_crd_with_provider_config(self):
        """Test building CRD with provider configuration."""
        config = HiveConfig(
            runtime=RuntimeConfig(),
            repo=RepoConfig(
                source="https://github.com/test/repo.git",
                evolve_files_and_ranges="main.py",
            ),
            sandbox=SandboxConfig(),
            provider=ProviderConfig(
                gcp=GCPConfig(enabled=True, spot=True),
            ),
        )

        result = build_experiment_crd(config, "test-exp")

        assert result["spec"]["provider"]["gcp"]["enabled"] is True
        assert result["spec"]["provider"]["gcp"]["spot"] is True


class TestGenerateExperimentName:
    """Tests for generate_experiment_name function."""

    def test_generate_name_without_timestamp(self):
        """Test generating name without timestamp suffix."""
        result = generate_experiment_name("my-experiment")

        assert result == "my-experiment"

    @patch("cli.experiment.utiltime.now_2_hash")
    def test_generate_name_with_timestamp(self, mock_hash):
        """Test generating name with timestamp suffix."""
        mock_hash.return_value = "abc123"

        result = generate_experiment_name("my-exp-")

        assert result == "my-exp-abc123"
        mock_hash.assert_called_once()

    def test_generate_name_uppercase_raises_error(self):
        """Test that uppercase names raise ValueError."""
        with pytest.raises(ValueError, match="Experiment name must be lowercase"):
            generate_experiment_name("MyExperiment")

    def test_generate_name_mixed_case_raises_error(self):
        """Test that mixed case names raise ValueError."""
        with pytest.raises(ValueError, match="Experiment name must be lowercase"):
            generate_experiment_name("my-Experiment")

    def test_generate_name_with_numbers(self):
        """Test generating name with numbers."""
        result = generate_experiment_name("exp-123")

        assert result == "exp-123"

    def test_generate_name_with_hyphens(self):
        """Test generating name with hyphens."""
        result = generate_experiment_name("my-test-exp")

        assert result == "my-test-exp"

    def test_generate_name_exactly_63_chars(self):
        """Test generating name with exactly 63 characters (max allowed)."""
        # 63 character name
        name = "a" * 63
        result = generate_experiment_name(name)

        assert result == name
        assert len(result) == 63

    def test_generate_name_exceeds_63_chars(self):
        """Test that names exceeding 63 characters raise ValueError."""
        # 64 character name
        name = "a" * 64

        with pytest.raises(
            ValueError, match="Experiment name must be no more than 63 characters"
        ):
            generate_experiment_name(name)

    def test_generate_name_long_example(self):
        """Test the real-world long name example."""
        long_name = "maxcut-qaoa--evolve-p--optimise-mean90--multi-n--again-coordinator"

        with pytest.raises(
            ValueError, match="Experiment name must be no more than 63 characters"
        ):
            generate_experiment_name(long_name)

    @patch("cli.experiment.utiltime.now_2_hash")
    def test_generate_name_with_timestamp_exceeds_limit(self, mock_hash):
        """Test that base name + timestamp exceeding 63 chars raises ValueError."""
        mock_hash.return_value = "abc1234"  # 7 characters

        # Base name of 57 chars + "-" + 7 char hash = 65 chars total
        base_name = "a" * 57 + "-"

        with pytest.raises(
            ValueError, match="Experiment name must be no more than 63 characters"
        ):
            generate_experiment_name(base_name)

    @patch("cli.experiment.utiltime.now_2_hash")
    def test_generate_name_with_timestamp_exactly_63_chars(self, mock_hash):
        """Test that base name + timestamp with exactly 63 chars succeeds."""
        mock_hash.return_value = "abc1234"  # 7 characters

        # Base name: 56 chars including the dash + 7 char hash = 63 chars total
        base_name = "a" * 55 + "-"  # 56 chars total with the dash

        result = generate_experiment_name(base_name)

        assert len(result) == 63  # 56 + 7
        assert result == ("a" * 55) + "-abc1234"
