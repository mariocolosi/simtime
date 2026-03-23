from __future__ import annotations


class SimTimeError(Exception):
    """Base exception for all SimTime errors."""


class SchedulingError(SimTimeError):
    """Raised when an event cannot be scheduled."""

    def __init__(self, reason: str):
        super().__init__(reason)


class SimTimeWarning(UserWarning):
    """Warning issued for non-fatal simulation problems."""
