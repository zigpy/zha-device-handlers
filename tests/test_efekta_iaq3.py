"""Tests for EfektaLab EFEKTA_iAQ3 air quality sensor quirk."""

from unittest import mock

import pytest
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import AnalogInput
from zigpy.zcl.clusters.measurement import (
    CarbonDioxideConcentration,
    RelativeHumidity,
    TemperatureMeasurement,
)

from tests.common import ClusterListener
import zhaquirks
from zhaquirks.efekta.iaq3 import (
    CO2ConcentrationConfig,
    EfektaVocAnalogInput,
    EmulatedVOCMeasurement,
    RelativeHumidityConfig,
    TemperatureMeasurementConfig,
)

zhaquirks.setup()

# Test constants
MANUFACTURER = "EfektaLab"
MODEL = "EFEKTA_iAQ3"
ENDPOINT_IDS = [1, 2]


async def test_efekta_iaq3_device_creation(zigpy_device_from_v2_quirk):
    """Test EFEKTA_iAQ3 device is created correctly with custom clusters."""
    device = zigpy_device_from_v2_quirk(
        manufacturer=MANUFACTURER,
        model=MODEL,
        endpoint_ids=ENDPOINT_IDS,
    )

    assert device.manufacturer == MANUFACTURER
    assert device.model == MODEL

    # Verify endpoint 1 has custom clusters
    ep1 = device.endpoints[1]
    assert TemperatureMeasurement.cluster_id in ep1.in_clusters
    assert RelativeHumidity.cluster_id in ep1.in_clusters
    assert CarbonDioxideConcentration.cluster_id in ep1.in_clusters

    # Verify clusters are actually the custom versions
    temp_cluster = ep1.in_clusters[TemperatureMeasurement.cluster_id]
    assert isinstance(temp_cluster, TemperatureMeasurementConfig)

    humidity_cluster = ep1.in_clusters[RelativeHumidity.cluster_id]
    assert isinstance(humidity_cluster, RelativeHumidityConfig)

    co2_cluster = ep1.in_clusters[CarbonDioxideConcentration.cluster_id]
    assert isinstance(co2_cluster, CO2ConcentrationConfig)

    # Verify endpoint 2 has VOC clusters
    ep2 = device.endpoints[2]
    assert AnalogInput.cluster_id in ep2.in_clusters
    assert EmulatedVOCMeasurement.cluster_id in ep2.in_clusters

    analog_cluster = ep2.in_clusters[AnalogInput.cluster_id]
    assert isinstance(analog_cluster, EfektaVocAnalogInput)

    voc_cluster = ep2.in_clusters[EmulatedVOCMeasurement.cluster_id]
    assert isinstance(voc_cluster, EmulatedVOCMeasurement)


async def test_voc_relay_functionality(zigpy_device_from_v2_quirk):
    """Test VOC value relay from AnalogInput to EmulatedVOCMeasurement."""
    device = zigpy_device_from_v2_quirk(
        manufacturer=MANUFACTURER,
        model=MODEL,
        endpoint_ids=ENDPOINT_IDS,
    )

    ep2 = device.endpoints[2]
    analog_cluster = ep2.in_clusters[AnalogInput.cluster_id]
    voc_cluster = ep2.in_clusters[EmulatedVOCMeasurement.cluster_id]

    # Set up listener for VOC cluster
    voc_listener = ClusterListener(voc_cluster)

    # Simulate AnalogInput present_value update
    test_voc_values = [50.0, 150.0, 250.0, 350.0]

    for test_value in test_voc_values:
        # Update AnalogInput present_value
        analog_cluster._update_attribute(EfektaVocAnalogInput.PRESENT_VALUE, test_value)

        # Verify VOC cluster was updated with the same value
        assert len(voc_listener.attribute_updates) > 0
        last_update = voc_listener.attribute_updates[-1]
        assert last_update == (0x0000, test_value)  # measured_value attribute

    # Verify total updates match test values
    assert len(voc_listener.attribute_updates) == len(test_voc_values)


async def test_voc_relay_ignores_none_values(zigpy_device_from_v2_quirk):
    """Test VOC relay ignores None values."""
    device = zigpy_device_from_v2_quirk(
        manufacturer=MANUFACTURER,
        model=MODEL,
        endpoint_ids=ENDPOINT_IDS,
    )

    ep2 = device.endpoints[2]
    analog_cluster = ep2.in_clusters[AnalogInput.cluster_id]
    voc_cluster = ep2.in_clusters[EmulatedVOCMeasurement.cluster_id]

    voc_listener = ClusterListener(voc_cluster)

    # Update with None value - should not trigger VOC update
    analog_cluster._update_attribute(EfektaVocAnalogInput.PRESENT_VALUE, None)

    # No updates should have occurred
    assert len(voc_listener.attribute_updates) == 0

    # Now update with valid value - should trigger update
    analog_cluster._update_attribute(EfektaVocAnalogInput.PRESENT_VALUE, 100.0)
    assert len(voc_listener.attribute_updates) == 1
    assert voc_listener.attribute_updates[0] == (0x0000, 100.0)


async def test_voc_relay_ignores_other_attributes(zigpy_device_from_v2_quirk):
    """Test VOC relay only relays present_value, not other attributes."""
    device = zigpy_device_from_v2_quirk(
        manufacturer=MANUFACTURER,
        model=MODEL,
        endpoint_ids=ENDPOINT_IDS,
    )

    ep2 = device.endpoints[2]
    analog_cluster = ep2.in_clusters[AnalogInput.cluster_id]
    voc_cluster = ep2.in_clusters[EmulatedVOCMeasurement.cluster_id]

    voc_listener = ClusterListener(voc_cluster)

    # Update a different attribute (not present_value)
    analog_cluster._update_attribute(0x001C, 50.0)  # description attribute

    # No VOC updates should have occurred
    assert len(voc_listener.attribute_updates) == 0


async def test_temperature_offset_attribute(zigpy_device_from_v2_quirk):
    """Test temperature offset configuration attribute."""
    device = zigpy_device_from_v2_quirk(
        manufacturer=MANUFACTURER,
        model=MODEL,
        endpoint_ids=ENDPOINT_IDS,
    )

    temp_cluster = device.endpoints[1].in_clusters[TemperatureMeasurement.cluster_id]

    # Verify the custom attribute exists in the cluster class
    assert hasattr(type(temp_cluster).AttributeDefs, "temperature_offset")
    temp_offset_attr = type(temp_cluster).AttributeDefs.temperature_offset
    assert temp_offset_attr.id == 0x0210


async def test_humidity_offset_attribute(zigpy_device_from_v2_quirk):
    """Test humidity offset configuration attribute."""
    device = zigpy_device_from_v2_quirk(
        manufacturer=MANUFACTURER,
        model=MODEL,
        endpoint_ids=ENDPOINT_IDS,
    )

    humidity_cluster = device.endpoints[1].in_clusters[RelativeHumidity.cluster_id]

    # Verify the custom attribute exists in the cluster class
    assert hasattr(type(humidity_cluster).AttributeDefs, "humidity_offset")
    humidity_offset_attr = type(humidity_cluster).AttributeDefs.humidity_offset
    assert humidity_offset_attr.id == 0x0210


async def test_co2_configuration_attributes(zigpy_device_from_v2_quirk):
    """Test CO2 sensor configuration attributes exist."""
    device = zigpy_device_from_v2_quirk(
        manufacturer=MANUFACTURER,
        model=MODEL,
        endpoint_ids=ENDPOINT_IDS,
    )

    co2_cluster = device.endpoints[1].in_clusters[CarbonDioxideConcentration.cluster_id]

    # Test key configuration attributes exist in the cluster class
    config_attrs = [
        "forced_recalibration",
        "auto_brightness",
        "long_chart_period",
        "set_altitude",
        "factory_reset_co2",
        "manual_forced_recalibration",
        "enable_co2",
        "high_co2",
        "low_co2",
        "invert_logic_co2",
        "rotate",
        "internal_or_external",
        "night_onoff_backlight",
        "automatic_scal",
        "long_chart_period2",
        "night_on_backlight",
        "night_off_backlight",
    ]

    for attr_name in config_attrs:
        assert hasattr(type(co2_cluster).AttributeDefs, attr_name), (
            f"Missing attribute: {attr_name}"
        )


async def test_voc_bind_and_configure_reporting(zigpy_device_from_v2_quirk):
    """Test VOC cluster bind configures reporting on AnalogInput cluster."""
    device = zigpy_device_from_v2_quirk(
        manufacturer=MANUFACTURER,
        model=MODEL,
        endpoint_ids=ENDPOINT_IDS,
    )

    ep2 = device.endpoints[2]
    analog_cluster = ep2.in_clusters[AnalogInput.cluster_id]
    voc_cluster = ep2.in_clusters[EmulatedVOCMeasurement.cluster_id]

    # Mock the bind and configure_reporting methods
    patch_analog_bind = mock.patch.object(
        analog_cluster,
        "bind",
        mock.AsyncMock(return_value=[foundation.Status.SUCCESS]),
    )

    patch_analog_configure = mock.patch.object(
        analog_cluster,
        "configure_reporting",
        mock.AsyncMock(return_value=[foundation.Status.SUCCESS]),
    )

    with patch_analog_bind, patch_analog_configure:
        # Call bind on the VOC cluster
        result = await voc_cluster.bind()

        # Verify bind was called on the AnalogInput cluster
        assert analog_cluster.bind.called

        # Verify configure_reporting was called with correct parameters
        assert analog_cluster.configure_reporting.called
        call_args = analog_cluster.configure_reporting.call_args[0]
        assert call_args[0] == EfektaVocAnalogInput.PRESENT_VALUE  # attribute
        assert call_args[1] == 30  # min_interval
        assert call_args[2] == 600  # max_interval
        assert call_args[3] == 1.0  # reportable_change

        # Result should be from the AnalogInput bind
        assert result == [foundation.Status.SUCCESS]


@pytest.mark.parametrize(
    "attr_name,attr_id",
    [
        ("temperature_offset", 0x0210),
        ("humidity_offset", 0x0210),
    ],
)
def test_offset_attribute_definitions(attr_name, attr_id):
    """Test offset attribute definitions have correct IDs and types."""
    if attr_name == "temperature_offset":
        attr_def = TemperatureMeasurementConfig.AttributeDefs.temperature_offset
    else:
        attr_def = RelativeHumidityConfig.AttributeDefs.humidity_offset

    assert attr_def.id == attr_id
    # Verify type is defined (int16s)
    assert attr_def.type is not None
