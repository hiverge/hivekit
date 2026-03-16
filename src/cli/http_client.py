import os
from typing import Any, Dict, Optional

import requests
from authlib.integrations.requests_client import OAuth2Session
from rich.console import Console

console = Console()


class HttpClient:
    """HTTP client for communicating with the Hive backend server."""

    def __init__(self, base_url: Optional[str] = None, token_path: Optional[str] = None):
        """
        Initialize the HTTP client.

        Args:
            base_url: Base URL of the backend server (defaults to env var HIVE_API_ENDPOINT)
            token_path: Path to JWT token file (defaults to ~/.hive/token)
        """
        self.base_url = base_url or os.getenv("HIVE_API_ENDPOINT", "http://localhost:8080/api/v1")

        # Read JWT token from file
        self.token_path = token_path or os.path.expandvars("$HOME/.hive/token")
        self.auth_token = self._read_token()

        # Remove trailing slash from base URL
        self.base_url = self.base_url.rstrip("/")

        # Create OAuth2 session if token is available
        if self.auth_token:
            self.session = OAuth2Session(
                token={"access_token": self.auth_token, "token_type": "Bearer"}
            )
        else:
            self.session = requests.Session()

    def _read_token(self) -> str:
        """Read JWT token from file."""
        if not os.path.exists(self.token_path):
            console.print(f"[yellow]Warning: Token file not found at {self.token_path}[/yellow]")
            return ""

        try:
            with open(self.token_path, "r") as f:
                token = f.read().strip()
            return token
        except Exception as e:
            console.print(
                f"[yellow]Warning: Failed to read token from {self.token_path}: {e}[/yellow]"
            )
            return ""

    def _get_headers(self) -> Dict[str, str]:
        """Get common headers for all requests."""
        headers = {
            "Content-Type": "application/json",
        }
        return headers

    def create_experiment(self, experiment_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new experiment.

        Args:
            experiment_data: Experiment CRD data to send

        Returns:
            Created experiment data from the server

        Raises:
            requests.exceptions.RequestException: If the request fails
        """
        url = f"{self.base_url}/experiments"
        headers = self._get_headers()

        try:
            response = self.session.post(url, json=experiment_data, headers=headers, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            error_msg = f"Failed to create experiment: {e}"
            if e.response is not None:
                try:
                    error_detail = e.response.json()
                    if "error" in error_detail:
                        error_msg = f"Failed to create experiment: {error_detail['error']}"
                except Exception:
                    error_msg = f"Failed to create experiment: {e.response.text}"
            raise Exception(error_msg) from e
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to connect to backend server at {url}: {e}") from e

    def get_experiment(self, name: str) -> Dict[str, Any]:
        """
        Get an experiment by name.

        Args:
            name: Experiment name

        Returns:
            Experiment data from the server

        Raises:
            requests.exceptions.RequestException: If the request fails
        """
        url = f"{self.base_url}/experiments/{name}"
        headers = self._get_headers()

        try:
            response = self.session.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to get experiment: {e}") from e

    def list_experiments(self) -> Dict[str, Any]:
        """
        List experiments.

        Returns:
            List of experiments from the server

        Raises:
            requests.exceptions.RequestException: If the request fails
        """
        url = f"{self.base_url}/experiments"
        headers = self._get_headers()

        try:
            response = self.session.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to list experiments: {e}") from e

    def delete_experiment(self, name: str) -> Dict[str, Any]:
        """
        Delete an experiment.

        Args:
            name: Experiment name

        Returns:
            Response from the server

        Raises:
            requests.exceptions.RequestException: If the request fails
        """
        url = f"{self.base_url}/experiments/{name}"
        headers = self._get_headers()

        try:
            response = self.session.delete(url, headers=headers, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to delete experiment: {e}") from e
