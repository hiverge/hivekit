"""
Tests for the authentication utility functions.
"""

from cli.auth.auth_utils import get_machine_id


class TestGetMachineId:
    """
    Tests for the `get_machine_id` function. There isn't much we can test here, but
    we can at least check that the function works.
    """

    def test_returns_non_empty_string(self) -> None:
        """
        Test that get_machine_id returns a non-empty string.
        """
        # when
        result = get_machine_id()

        # then
        assert len(result) > 0

    def test_returns_consistent_value(self) -> None:
        """
        Test that get_machine_id returns the same value on repeated calls.
        """
        # when
        first = get_machine_id()
        second = get_machine_id()

        # then
        assert first == second
