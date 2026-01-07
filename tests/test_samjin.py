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


async def test_samjin_battery_none_value(zigpy_device_from_quirk):
    """Test that None battery percentage is passed through unchanged."""
    device = zigpy_device_from_quirk(SamjinMotion)
    power_cluster = device.endpoints[1].power

    listener = ClusterListener(power_cluster)
    battery_attr_id = PowerConfiguration.AttributeDefs.battery_percentage_remaining.id

    power_cluster.update_attribute(battery_attr_id, None)

    assert len(listener.attribute_updates) == 1
    assert listener.attribute_updates[0][1] is None


@pytest.mark.parametrize(
    "voltage_100mv, expected_percentage",
    [
        # Voltage in 100mV units, percentage in 0-200 scale
        # Formula: percent = (volts - 2.1) / (3.0 - 2.1) * 200
        (30, 200),  # 3.0V = 100% = 200
        (21, 0),  # 2.1V = 0% = 0
        (25, 88),  # 2.5V ~= 44% = ~88 (actually 88.88, truncated to 88)
        (27, 133),  # 2.7V ~= 66.7% = ~133
        (20, 0),  # 2.0V below min, clamped to 0
        (35, 200),  # 3.5V above max, clamped to 200
    ],
)
async def test_samjin_battery_voltage_fallback(
    zigpy_device_from_quirk, voltage_100mv, expected_percentage
):
    """Test voltage-to-percentage fallback when percentage not reported.

    When battery_percentage_remaining is not available, the cluster calculates
    it from battery_voltage using CR2 battery thresholds (2.1V - 3.0V).
    """
    device = zigpy_device_from_quirk(SamjinMotion)
    power_cluster = device.endpoints[1].power

    listener = ClusterListener(power_cluster)
    voltage_attr_id = PowerConfiguration.AttributeDefs.battery_voltage.id
    battery_attr_id = PowerConfiguration.AttributeDefs.battery_percentage_remaining.id

    # Send voltage update (percentage not yet set)
    power_cluster.update_attribute(voltage_attr_id, voltage_100mv)

    # Should have 2 updates: voltage and calculated percentage
    assert len(listener.attribute_updates) == 2
    assert listener.attribute_updates[0][0] == voltage_attr_id
    assert listener.attribute_updates[0][1] == voltage_100mv
    assert listener.attribute_updates[1][0] == battery_attr_id
    assert listener.attribute_updates[1][1] == expected_percentage


async def test_samjin_battery_voltage_no_override(zigpy_device_from_quirk):
    """Test that voltage does not override existing percentage."""
    device = zigpy_device_from_quirk(SamjinMotion)
    power_cluster = device.endpoints[1].power

    listener = ClusterListener(power_cluster)
    voltage_attr_id = PowerConfiguration.AttributeDefs.battery_voltage.id
    battery_attr_id = PowerConfiguration.AttributeDefs.battery_percentage_remaining.id

    # First set percentage (will be corrected by formula)
    # Raw 200 -> corrected 200
    power_cluster.update_attribute(battery_attr_id, 200)
    assert len(listener.attribute_updates) == 1
    assert listener.attribute_updates[0][1] == 200

    # Now send voltage - should NOT override percentage
    power_cluster.update_attribute(voltage_attr_id, 25)

    # Should only have voltage update, no new percentage update
    assert len(listener.attribute_updates) == 2
    assert listener.attribute_updates[1][0] == voltage_attr_id
    assert listener.attribute_updates[1][1] == 25
