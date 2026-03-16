from typing import Any, Dict

from cli.config import HiveConfig
from cli.utils import time as utiltime


def build_experiment_crd(config: HiveConfig, experiment_name: str) -> Dict[str, Any]:
    """
    Build a Kubernetes Experiment CRD from HiveConfig.

    Args:
        config: The Hive configuration
        experiment_name: Name of the experiment

    Returns:
        Dictionary representing the Experiment CRD
    """
    # Build the basic experiment structure
    experiment = {
        "apiVersion": "core.hiverge.io/v1alpha1",
        "kind": "Experiment",
        "metadata": {
            "name": experiment_name,
        },
        "spec": {
            "runtime": {
                "numAgents": config.runtime.num_agents,
                "maxRuntimeSeconds": config.runtime.max_runtime_seconds,
                "maxIterations": config.runtime.max_iterations,
            },
            "repo": {
                "source": config.repo.source,
                "branch": config.repo.branch,
                "evaluationScript": config.repo.evaluation_script,
                "evolveFilesAndRanges": config.repo.evolve_files_and_ranges,
            },
            "sandbox": {
                "timeout": config.sandbox.timeout,
                "resources": {
                    "cpu": config.sandbox.resources.cpu,
                    "memory": config.sandbox.resources.memory,
                },
            },
        },
    }

    # Add optional repo fields
    if config.repo.include_files_and_ranges:
        experiment["spec"]["repo"]["includeFilesAndRanges"] = config.repo.include_files_and_ranges

    # Add optional sandbox fields
    if config.sandbox.image:
        experiment["spec"]["sandbox"]["image"] = config.sandbox.image

    if config.sandbox.build_args:
        experiment["spec"]["sandbox"]["buildArgs"] = config.sandbox.build_args

    if config.sandbox.build_secret:
        experiment["spec"]["sandbox"]["buildSecret"] = config.sandbox.build_secret

    if config.sandbox.resources.accelerators:
        experiment["spec"]["sandbox"]["resources"]["accelerators"] = (
            config.sandbox.resources.accelerators
        )

    if config.sandbox.resources.shmsize:
        experiment["spec"]["sandbox"]["resources"]["shmsize"] = config.sandbox.resources.shmsize

    if config.sandbox.resources.extended_resources:
        experiment["spec"]["sandbox"]["resources"]["extendedResources"] = (
            config.sandbox.resources.extended_resources
        )

    if config.sandbox.envs:
        experiment["spec"]["sandbox"]["envs"] = [
            {"name": env.name, "value": env.value} for env in config.sandbox.envs
        ]

    if config.sandbox.preprocessor:
        experiment["spec"]["sandbox"]["preprocessor"] = config.sandbox.preprocessor
    elif config.sandbox.pre_processor:
        # Handle deprecated field
        experiment["spec"]["sandbox"]["preprocessor"] = config.sandbox.pre_processor

    if config.sandbox.services:
        experiment["spec"]["sandbox"]["services"] = [
            {
                "name": svc.name,
                "image": svc.image,
                **(
                    {"ports": [{"port": p.port, "protocol": p.protocol} for p in svc.ports]}
                    if svc.ports
                    else {}
                ),
                **(
                    {"envs": [{"name": e.name, "value": e.value} for e in svc.envs]}
                    if svc.envs
                    else {}
                ),
                **({"command": svc.command} if svc.command else {}),
                **({"args": svc.args} if svc.args else {}),
                "resources": {
                    "cpu": svc.resources.cpu,
                    "memory": svc.resources.memory,
                },
            }
            for svc in config.sandbox.services
        ]

    # Add optional prompt configuration
    if config.prompt:
        experiment["spec"]["prompt"] = {}
        if config.prompt.context:
            experiment["spec"]["prompt"]["context"] = config.prompt.context
        if config.prompt.ideas:
            experiment["spec"]["prompt"]["ideas"] = config.prompt.ideas
        if config.prompt.enable_evolution:
            experiment["spec"]["prompt"]["enableEvolution"] = config.prompt.enable_evolution

    # Add coordinator config
    if config.coordinator_config_name:
        experiment["spec"]["coordinatorConfigName"] = config.coordinator_config_name

    # Add provider configuration
    if config.provider:
        experiment["spec"]["provider"] = {}
        if config.provider.gcp:
            experiment["spec"]["provider"]["gcp"] = {
                "enabled": config.provider.gcp.enabled,
                "spot": config.provider.gcp.spot,
            }
        if config.provider.aws:
            experiment["spec"]["provider"]["aws"] = {
                "enabled": config.provider.aws.enabled,
                "spot": config.provider.aws.spot,
            }

    return experiment


def generate_experiment_name(base_name: str) -> str:
    """
    Generate a unique experiment name based on the base name and current timestamp.
    If the base name ends with '-', it will be suffixed with a timestamp.
    """

    if any(c.isupper() for c in base_name):
        raise ValueError("Experiment name must be lowercase.")

    experiment_name = base_name

    # A generated experiment name will be returned directly.
    if experiment_name.endswith("-"):
        hash = utiltime.now_2_hash()
        experiment_name = f"{base_name}{hash}"

    return experiment_name
