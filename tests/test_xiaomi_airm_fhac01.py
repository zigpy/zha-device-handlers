"""Test Aqara air quality monitor (lumi.airm.fhac01) quirk."""

from zigpy.zcl.clusters.general import DeviceTemperature
from zigpy.zcl.clusters.measurement import CarbonDioxideConcentration

from zhaquirks.xiaomi.aqara.airm_fhac01 import (
    CarbonDioxideConcentrationCluster,
    CustomDeviceTemperature,
)


def test_co2_concentration_cluster_scaling():
    """Test CO2 concentration cluster scaling functionality."""
    cluster = CarbonDioxideConcentrationCluster(None, None)

    # Test normal CO2 value with 6 extra zeros
    test_value = 400_000_000  # Should represent 400 ppm
    expected_value = 400.0  # After scaling

    cluster._update_attribute(
        CarbonDioxideConcentration.AttributeDefs.measured_value.id, test_value
    )

    # Check that the value was correctly scaled
    actual_value = cluster.get("measured_value")
    assert actual_value == expected_value


def test_co2_concentration_cluster_edge_cases():
    """Test CO2 concentration cluster with edge cases."""
    cluster = CarbonDioxideConcentrationCluster(None, None)

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


def test_co2_concentration_other_attributes_unchanged():
    """Test that other CO2 cluster attributes are not affected by scaling."""
    cluster = CarbonDioxideConcentrationCluster(None, None)

    # Test min_measured_value attribute (should not be scaled)
    test_value = 1000
    cluster._update_attribute(
        CarbonDioxideConcentration.AttributeDefs.min_measured_value.id, test_value
    )

    actual_value = cluster.get("min_measured_value")
    assert actual_value == test_value  # No scaling


def test_device_temperature_cluster_scaling():
    """Test device temperature cluster scaling functionality."""
    cluster = CustomDeviceTemperature(None, None)

    # Test normal temperature value divided by 100
    test_value = 25  # Should represent 25°C
    expected_value = 2500  # After scaling (25°C * 100)

    cluster._update_attribute(
        DeviceTemperature.AttributeDefs.current_temperature.id, test_value
    )

    # Check that the value was correctly scaled
    actual_value = cluster.get("current_temperature")
    assert actual_value == expected_value


def test_device_temperature_cluster_edge_cases():
    """Test device temperature cluster with edge cases."""
    cluster = CustomDeviceTemperature(None, None)

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


def test_device_temperature_other_attributes_unchanged():
    """Test that other device temperature cluster attributes are not affected by scaling."""
    cluster = CustomDeviceTemperature(None, None)

    # Test min_temp_experienced attribute (should not be scaled)
    test_value = 20
    cluster._update_attribute(
        DeviceTemperature.AttributeDefs.min_temp_experienced.id, test_value
    )

    actual_value = cluster.get("min_temp_experienced")
    assert actual_value == test_value  # No scaling


def test_cluster_inheritance():
    """Test that clusters properly inherit from their base classes."""
    co2_cluster = CarbonDioxideConcentrationCluster(None, None)
    temp_cluster = CustomDeviceTemperature(None, None)

    # Check that they are instances of the correct base classes
    assert isinstance(co2_cluster, CarbonDioxideConcentration)
    assert isinstance(temp_cluster, DeviceTemperature)

    # Check that they have the expected cluster IDs
    assert co2_cluster.cluster_id == CarbonDioxideConcentration.cluster_id
    assert temp_cluster.cluster_id == DeviceTemperature.cluster_id
