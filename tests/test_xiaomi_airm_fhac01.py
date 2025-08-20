"""Test Aqara air quality monitor (lumi.airm.fhac01) quirk."""

import pytest
from zigpy.zcl.clusters.general import DeviceTemperature
from zigpy.zcl.clusters.measurement import (
    CarbonDioxideConcentration,
    RelativeHumidity,
    TemperatureMeasurement,
)

from tests.common import ClusterListener
import zhaquirks
from zhaquirks.xiaomi import LUMI
import zhaquirks.xiaomi.aqara.airm_fhac01  # Import the quirk to register it

zhaquirks.setup()


@pytest.fixture
def air_quality_device(zigpy_device_from_v2_quirk):
    """Aqara air quality monitor device."""
    return zigpy_device_from_v2_quirk(LUMI, "lumi.airm.fhac01")


def test_device_creation(air_quality_device):
    """Test that the device is created correctly with all expected clusters."""
    device = air_quality_device

    # Check that the device was created
    assert device is not None
    assert device.manufacturer == LUMI
    assert device.model == "lumi.airm.fhac01"

    # Check that endpoint 1 exists
    assert 1 in device.endpoints
    endpoint = device.endpoints[1]

    # Check that all expected clusters are present
    expected_clusters = {
        CarbonDioxideConcentration.cluster_id,
        DeviceTemperature.cluster_id,
        TemperatureMeasurement.cluster_id,
        RelativeHumidity.cluster_id,
    }

    for cluster_id in expected_clusters:
        assert cluster_id in endpoint.in_clusters, f"Missing cluster {cluster_id}"


def test_co2_concentration_scaling(air_quality_device):
    """Test CO2 concentration cluster scaling (divide by 1e6)."""
    device = air_quality_device
    co2_cluster = device.endpoints[1].carbon_dioxide_concentration
    co2_listener = ClusterListener(co2_cluster)

    # Test normal CO2 value with 6 extra zeros
    test_value = 400_000_000  # Should represent 400 ppm
    expected_value = 400.0  # After scaling

    co2_cluster._update_attribute(
        CarbonDioxideConcentration.AttributeDefs.measured_value.id, test_value
    )

    assert len(co2_listener.attribute_updates) == 1
    assert (
        co2_listener.attribute_updates[0][0]
        == CarbonDioxideConcentration.AttributeDefs.measured_value.id
    )
    assert co2_listener.attribute_updates[0][1] == expected_value


def test_co2_concentration_scaling_edge_cases(air_quality_device):
    """Test CO2 concentration scaling with edge cases."""
    device = air_quality_device
    co2_cluster = device.endpoints[1].carbon_dioxide_concentration
    co2_listener = ClusterListener(co2_cluster)

    test_cases = [
        (0, 0.0),  # Zero value
        (1_000_000, 1.0),  # 1 ppm
        (2000_000_000, 2000.0),  # 2000 ppm (high but reasonable)
    ]

    for i, (test_value, expected_value) in enumerate(test_cases):
        co2_cluster._update_attribute(
            CarbonDioxideConcentration.AttributeDefs.measured_value.id, test_value
        )

        assert len(co2_listener.attribute_updates) == i + 1
        assert co2_listener.attribute_updates[i][1] == expected_value


def test_device_temperature_scaling(air_quality_device):
    """Test device temperature cluster scaling (multiply by 100)."""
    device = air_quality_device
    temp_cluster = device.endpoints[1].device_temperature
    temp_listener = ClusterListener(temp_cluster)

    # Test normal temperature value divided by 100
    test_value = 25  # Should represent 25°C
    expected_value = 2500  # After scaling (25°C * 100)

    temp_cluster._update_attribute(
        DeviceTemperature.AttributeDefs.current_temperature.id, test_value
    )

    assert len(temp_listener.attribute_updates) == 1
    assert (
        temp_listener.attribute_updates[0][0]
        == DeviceTemperature.AttributeDefs.current_temperature.id
    )
    assert temp_listener.attribute_updates[0][1] == expected_value


def test_device_temperature_scaling_edge_cases(air_quality_device):
    """Test device temperature scaling with edge cases."""
    device = air_quality_device
    temp_cluster = device.endpoints[1].device_temperature
    temp_listener = ClusterListener(temp_cluster)

    test_cases = [
        (0, 0),  # 0°C
        (-10, -1000),  # -10°C (negative temperature)
        (50, 5000),  # 50°C (high temperature)
        (1, 100),  # 1°C
    ]

    for i, (test_value, expected_value) in enumerate(test_cases):
        temp_cluster._update_attribute(
            DeviceTemperature.AttributeDefs.current_temperature.id, test_value
        )

        assert len(temp_listener.attribute_updates) == i + 1
        assert temp_listener.attribute_updates[i][1] == expected_value


def test_other_clusters_unchanged(air_quality_device):
    """Test that other clusters work normally without scaling."""
    device = air_quality_device

    # Test TemperatureMeasurement cluster (should work normally)
    temp_measurement_cluster = device.endpoints[1].temperature
    temp_measurement_listener = ClusterListener(temp_measurement_cluster)

    test_value = 2500  # 25.0°C in centidegrees
    temp_measurement_cluster._update_attribute(
        TemperatureMeasurement.AttributeDefs.measured_value.id, test_value
    )

    assert len(temp_measurement_listener.attribute_updates) == 1
    assert temp_measurement_listener.attribute_updates[0][1] == test_value  # No scaling

    # Test RelativeHumidity cluster (should work normally)
    humidity_cluster = device.endpoints[1].humidity
    humidity_listener = ClusterListener(humidity_cluster)

    test_value = 5000  # 50.0% humidity
    humidity_cluster._update_attribute(
        RelativeHumidity.AttributeDefs.measured_value.id, test_value
    )

    assert len(humidity_listener.attribute_updates) == 1
    assert humidity_listener.attribute_updates[0][1] == test_value  # No scaling


def test_co2_other_attributes_unchanged(air_quality_device):
    """Test that other CO2 cluster attributes are not affected by scaling."""
    device = air_quality_device
    co2_cluster = device.endpoints[1].carbon_dioxide_concentration
    co2_listener = ClusterListener(co2_cluster)

    # Test min_measured_value attribute (should not be scaled)
    test_value = 1000
    co2_cluster._update_attribute(
        CarbonDioxideConcentration.AttributeDefs.min_measured_value.id, test_value
    )

    assert len(co2_listener.attribute_updates) == 1
    assert co2_listener.attribute_updates[0][1] == test_value  # No scaling


def test_device_temperature_other_attributes_unchanged(air_quality_device):
    """Test that other device temperature cluster attributes are not affected by scaling."""
    device = air_quality_device
    temp_cluster = device.endpoints[1].device_temperature
    temp_listener = ClusterListener(temp_cluster)

    # Test min_temp_experienced attribute (should not be scaled)
    test_value = 20
    temp_cluster._update_attribute(
        DeviceTemperature.AttributeDefs.min_temp_experienced.id, test_value
    )

    assert len(temp_listener.attribute_updates) == 1
    assert temp_listener.attribute_updates[0][1] == test_value  # No scaling


def test_quirk_registration():
    """Test that the quirk is properly registered."""
    import zigpy.quirks

    # Check that the quirk is registered for the correct manufacturer and model
    registry = zigpy.quirks.DEVICE_REGISTRY

    # For v2 quirks, check the registry_v2
    found_quirk = False
    for quirk_entries in registry.registry_v2.values():
        for entry in quirk_entries:
            if entry.manufacturer == LUMI and entry.model == "lumi.airm.fhac01":
                found_quirk = True
                break
        if found_quirk:
            break

    assert found_quirk, "Quirk not found in registry"
