from argcomplete.completers import FilesCompleter

from cli.config import load_config
from cli.http_client import create_http_client
from cli.utils.config_paths import get_config_path


def config_file_completer(prefix, **kwargs):
    """Autocomplete for config file paths."""
    try:
        completer = FilesCompleter()
        return completer(prefix, **kwargs)
    except Exception:
        return []


def experiment_completer(prefix, **kwargs):
    """Autocomplete for experiment names by fetching from the server."""
    try:
        config = load_config(file_path=get_config_path())
        client = create_http_client(organization_id=config.organization_id)

        # Fetch experiments from server
        result = client.list_experiments()
        experiments = result.get("experiments", [])

        # Extract experiment names
        names = [exp.get("metadata", {}).get("name", "") for exp in experiments]
        names = [name for name in names if name]  # Filter out empty names

        # Filter by prefix if provided
        if prefix:
            names = [name for name in names if name.startswith(prefix)]

        return names
    except Exception:
        # Return empty list on any error to not break completion
        return []
