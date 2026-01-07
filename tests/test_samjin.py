"""Tests for Samjin quirks."""

import pytest
from zigpy.zcl.clusters.general import PowerConfiguration

from tests.common import ClusterListener
import zhaquirks
from zhaquirks.samjin.motion import SamjinMotion, SamjinPowerConfiguration

zhaquirks.setup()


def test_samjin_motion_signature():
    """Test SamjinMotion quirk signature and replacement."""
    assert SamjinMotion.signature
    assert SamjinMotion.replacement
    assert SamjinMotion.replacement.get("endpoints")


def test_samjin_motion_power_configuration_constants():
    """Test battery voltage threshold constants."""
    assert SamjinPowerConfiguration.MIN_VOLTS == 2.1
    assert SamjinPowerConfiguration.MAX_VOLTS == 3.0
    assert SamjinPowerConfiguration.BATTERY_PERCENTAGE_REMAINING == 0x0021
    assert SamjinPowerConfiguration.BATTERY_VOLTAGE == 0x0020


async def test_samjin_motion_quirk_match(zigpy_device_from_quirk):
    """Test that the quirk properly matches the device signature."""
    device = zigpy_device_from_quirk(SamjinMotion)

    assert device.manufacturer == "Samjin"
    assert device.model == "motion"

    # Check that replacement clusters are applied
    ep = device.endpoints[1]
    assert 0x0001 in ep.in_clusters  # PowerConfiguration
    assert 0x0500 in ep.in_clusters  # IasZone
    assert 0x0402 in ep.in_clusters  # TemperatureMeasurement


@pytest.mark.parametrize(
    "raw_value, expected_corrected",
    [
        # Formula: corrected = rawValue - (200 - rawValue) // 2
        (200, 200),  # 100% -> 100% (200 - 0 = 200)
        (100, 50),  # 50% raw -> 25% (100 - 50 = 50)
        (150, 125),  # 75% raw -> 62.5% (150 - 25 = 125)
        (50, 0),  # 25% raw -> 0% (50 - 75 = -25, clamped to 0)
        (0, 0),  # 0% -> 0% (clamped)
        (180, 170),  # 90% raw -> 85% (180 - 10 = 170)
        (120, 80),  # 60% raw -> 40% (120 - 40 = 80)
    ],
)
async def test_samjin_battery_percentage_correction(
    zigpy_device_from_quirk, raw_value, expected_corrected
):
    """Test SmartThings battery percentage correction formula.

    Samjin devices report non-linear battery values. The correction formula
    from SmartThings driver is: corrected = rawValue - (200 - rawValue) / 2
    """
    device = zigpy_device_from_quirk(SamjinMotion)
    power_cluster = device.endpoints[1].power

    listener = ClusterListener(power_cluster)
    battery_attr_id = PowerConfiguration.AttributeDefs.battery_percentage_remaining.id

    power_cluster.update_attribute(battery_attr_id, raw_value)

    assert len(listener.attribute_updates) == 1
    assert listener.attribute_updates[0][0] == battery_attr_id
    assert listener.attribute_updates[0][1] == expected_corrected


async def test_samjin_battery_percentage_clamping_high(zigpy_device_from_quirk):
    """Test that battery percentage is clamped to max 200."""
    device = zigpy_device_from_quirk(SamjinMotion)
    power_cluster = device.endpoints[1].power

    listener = ClusterListener(power_cluster)
    battery_attr_id = PowerConfiguration.AttributeDefs.battery_percentage_remaining.id

    # Value above 200 should be clamped after formula
    # For value=250: 250 - (200 - 250) // 2 = 250 - (-25) = 275, clamped to 200
    power_cluster.update_attribute(battery_attr_id, 250)

    assert len(listener.attribute_updates) == 1
    assert listener.attribute_updates[0][1] == 200
