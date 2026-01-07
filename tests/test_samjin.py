"""Tests for Samjin quirks."""

import zhaquirks
from zhaquirks.samjin.motion import SamjinMotion, SamjinPowerConfiguration

zhaquirks.setup()


def test_samjin_motion_signature():
    """Test SamjinMotion quirk signature and replacement."""
    assert SamjinMotion.signature
    assert SamjinMotion.replacement
    assert SamjinMotion.replacement.get("endpoints")


def test_samjin_motion_power_configuration_battery_calculation():
    """Test battery percentage calculation from voltage."""
    cluster = SamjinPowerConfiguration

    # Test voltage thresholds
    assert cluster.MIN_VOLTS == 2.1
    assert cluster.MAX_VOLTS == 3.0


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
