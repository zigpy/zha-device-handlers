"""Mock utilities that are async aware."""

from unittest.mock import *  # noqa: F401, F403


class _IntSentinelObject(int):
    """Sentinel-like object that is also an integer subclass.

    Allows sentinels to be used
    in loggers that perform int-specific string formatting.
    """

    def __new__(cls, name):
        instance = super().__new__(cls, 0)
        instance.name = name
        return instance

    def __repr__(self):
        return f"int_sentinel.{self.name}"

    def __hash__(self):
        return hash((int(self), self.name))

    def __eq__(self, other):
        return self is other

    __str__ = __reduce__ = __repr__


class _IntSentinel:
    def __init__(self):
        self._sentinels = {}

    def __getattr__(self, name):
        if name == "__bases__":
            raise AttributeError
        return self._sentinels.setdefault(name, _IntSentinelObject(name))

    def __reduce__(self):
        return "int_sentinel"


int_sentinel = _IntSentinel()
