"""Test Aqara air quality monitor (lumi.airm.fhac01) quirk."""

from zigpy.zcl.clusters.general import DeviceTemperature
from zigpy.zcl.clusters.measurement import CarbonDioxideConcentration

import zhaquirks.xiaomi.aqara.airm_fhac01  # noqa: F401 - register quirk


def test_co2_concentration_cluster_scaling(zigpy_device_from_v2_quirk):
    """Test CO2 concentration cluster scaling functionality."""
    device = zigpy_device_from_v2_quirk("LUMI", "lumi.airm.fhac01")
    cluster = device.endpoints[1].carbon_dioxide_concentration

    # Test normal CO2 value with 6 extra zeros
    test_value = 400_000_000  # Should represent 400 ppm
    expected_value = 400.0  # After scaling

    cluster._update_attribute(
        CarbonDioxideConcentration.AttributeDefs.measured_value.id, test_value
    )

    # Check that the value was correctly scaled
    actual_value = cluster.get("measured_value")
    assert actual_value == expected_value


def test_co2_concentration_cluster_edge_cases(zigpy_device_from_v2_quirk):
    """Test CO2 concentration cluster with edge cases."""
    device = zigpy_device_from_v2_quirk("LUMI", "lumi.airm.fhac01")
    cluster = device.endpoints[1].carbon_dioxide_concentration

    test_cases = [
        (0, 0.0),  # Zero value
        (1_000_000, 1.0),  # 1 ppm
        (2000_000_000, 2000.0),  # 2000 ppm (high but reasonable)
    ]

    for test_value, expected_value in test_cases:
        cluster._update_attribute(
            CarbonDioxideConcentration.AttributeDefs.measured_value.id, test_value
        )
        actual_value = cluster.get("measured_value")
        assert actual_value == expected_value


def test_co2_concentration_other_attributes_unchanged(zigpy_device_from_v2_quirk):
    """Test that other CO2 cluster attributes are not affected by scaling."""
    device = zigpy_device_from_v2_quirk("LUMI", "lumi.airm.fhac01")
    cluster = device.endpoints[1].carbon_dioxide_concentration

    # Test min_measured_value attribute (should not be scaled)
    test_value = 1000
    cluster._update_attribute(
        CarbonDioxideConcentration.AttributeDefs.min_measured_value.id, test_value
    )

    actual_value = cluster.get("min_measured_value")
    assert actual_value == test_value  # No scaling


def test_device_temperature_cluster_scaling(zigpy_device_from_v2_quirk):
    """Test device temperature cluster scaling functionality."""
    device = zigpy_device_from_v2_quirk("LUMI", "lumi.airm.fhac01")
    cluster = device.endpoints[1].device_temperature

    # Test normal temperature value divided by 100
    test_value = 25  # Should represent 25°C
    expected_value = 2500  # After scaling (25°C * 100)

    cluster._update_attribute(
        DeviceTemperature.AttributeDefs.current_temperature.id, test_value
    )

    # Check that the value was correctly scaled
    actual_value = cluster.get("current_temperature")
    assert actual_value == expected_value


def test_device_temperature_cluster_edge_cases(zigpy_device_from_v2_quirk):
    """Test device temperature cluster with edge cases."""
    device = zigpy_device_from_v2_quirk("LUMI", "lumi.airm.fhac01")
    cluster = device.endpoints[1].device_temperature

    test_cases = [
        (0, 0),  # 0°C
        (-10, -1000),  # -10°C
        (100, 10000),  # 100°C
        (1, 100),  # 1°C
    ]

    for test_value, expected_value in test_cases:
        cluster._update_attribute(
            DeviceTemperature.AttributeDefs.current_temperature.id, test_value
        )
        actual_value = cluster.get("current_temperature")
        assert actual_value == expected_value


def test_device_temperature_other_attributes_unchanged(zigpy_device_from_v2_quirk):
    """Test that other device temperature cluster attributes are not affected by scaling."""
    device = zigpy_device_from_v2_quirk("LUMI", "lumi.airm.fhac01")
    cluster = device.endpoints[1].device_temperature

    # Test min_temp_experienced attribute (should not be scaled)
    test_value = 20
    cluster._update_attribute(
        DeviceTemperature.AttributeDefs.min_temp_experienced.id, test_value
    )

    actual_value = cluster.get("min_temp_experienced")
    assert actual_value == test_value  # No scaling
