from argcomplete.completers import FilesCompleter

from cli.http_client import create_http_client


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
        import os

        base_url = os.getenv("HIVE_API_ENDPOINT", "https://platform.hiverge.ai/api/v1")
        client = create_http_client(base_url=base_url, no_auth=True)

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
