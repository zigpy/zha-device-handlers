"""Fixtures for all tests."""

import sys
from unittest.mock import MagicMock

# Mock the zha module since it's not available in CI
from zhaquirks import DEVICE_REGISTRY as REAL_DEVICE_REGISTRY

# Mock the zha module since it's not available in CI
zha_mock = MagicMock()
zha_mock.quirks = MagicMock()

# Create a proper DEVICE_REGISTRY mock using the real one
device_registry_mock = MagicMock()
device_registry_mock.resolve = REAL_DEVICE_REGISTRY.resolve
device_registry_mock.match_entry = REAL_DEVICE_REGISTRY.match_entry

zha_mock.quirks = MagicMock()
zha_mock.quirks.DEVICE_REGISTRY = device_registry_mock
sys.modules["zha"] = zha_mock
sys.modules["zha.quirks"] = zha_mock.quirks
