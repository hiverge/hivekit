"""
Common configuration paths for the Hive CLI.
"""

import os

_CONFIG_DIR = os.path.expandvars("$HOME/.hive")
_CONFIG_PATH = os.path.join(_CONFIG_DIR, "config.yaml")


def get_config_dir() -> str:
    """
    Return the path to the Hive configuration directory.
    """
    return _CONFIG_DIR


def get_config_path() -> str:
    """
    Return the path to the Hive configuration file.
    """
    return _CONFIG_PATH
