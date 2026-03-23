"""
Authentication utility functions.
"""

import machineid


def get_machine_id() -> str:
    """
    Return a machine-specific identifier for credential encryption.
    """
    return machineid.id()
