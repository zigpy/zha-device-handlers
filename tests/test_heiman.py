"""Tests for Heiman custom quirks."""

from unittest.mock import MagicMock, patch
import pytest

# Import the custom cluster class
from zhaquirks.heiman.hs1rm_e import HeimanDeviceTemperature


@patch("zigpy.zcl.Cluster._update_attribute")
def test_heiman_temperature_scaling(mock_super_update):
    """Test if Heiman detector raw temperature values are correctly scaled by 100."""
    
    # 1. Initialize the custom cluster class with a mocked device object
    cluster = HeimanDeviceTemperature(MagicMock())

    # 2. Simulate the device reporting the temperature attribute (attrid=0x0000) with a raw value of 25
    # This should trigger the custom logic: 25 * 100 = 2500
    cluster._update_attribute(0x0000, 25)

    # Assert: Verify that super()._update_attribute was called with the scaled value of 2500
    mock_super_update.assert_called_with(0x0000, 2500)

    # 3. Simulate the device reporting a non-temperature attribute (e.g., attrid=0x0001)
    # Verify that it is not incorrectly scaled
    mock_super_update.reset_mock()
    cluster._update_attribute(0x0001, 25)

    # Assert: Non-temperature attribute values should remain unchanged (still 25)
    mock_super_update.assert_called_with(0x0001, 25)
    
    # 4. Simulate the device reporting a None value for temperature
    # Verify that it does not trigger a multiplication error
    mock_super_update.reset_mock()
    cluster._update_attribute(0x0000, None)
    mock_super_update.assert_called_with(0x0000, None)