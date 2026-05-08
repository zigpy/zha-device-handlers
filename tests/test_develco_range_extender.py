"""Tests for Frient range extender quirks."""

import itertools

import zigpy.quirks
from zigpy.quirks.v2 import EntityType
from zigpy.quirks.v2.homeassistant import PERCENTAGE
from zigpy.quirks.v2.homeassistant.binary_sensor import BinarySensorDeviceClass
from zigpy.zcl import ClusterType
from zigpy.zcl.clusters.general import PowerConfiguration
from zigpy.zcl.clusters.security import IasZone

import zhaquirks
from zhaquirks.develco.range_extender import RangeExtenderPowerConfiguration

zhaquirks.setup()


def _get_range_extender_quirk_entry(model: str):
    """Return the registered range extender quirk entry for a model."""
    for quirk in itertools.chain.from_iterable(
        zigpy.quirks.DEVICE_REGISTRY.registry_v2.values()
    ):
        if ("frient A/S", model) in {
            (metadata.manufacturer, metadata.model)
            for metadata in quirk.manufacturer_model_metadata
        }:
            return quirk

    raise AssertionError(f"{model} quirk not registered")


async def test_rexzb_111_replaces_power_config(zigpy_device_from_v2_quirk):
    """Test REXZB-111 replaces the PowerConfiguration cluster."""
    device = zigpy_device_from_v2_quirk(
        "frient A/S",
        "REXZB-111",
        endpoint_ids=[37],
        cluster_ids={
            37: {
                PowerConfiguration.cluster_id: ClusterType.Server,
                IasZone.cluster_id: ClusterType.Server,
            }
        },
    )

    endpoint = device.endpoints[37]
    assert isinstance(endpoint.power, RangeExtenderPowerConfiguration)
    assert endpoint.power.MIN_VOLTS == 3.2
    assert endpoint.power.MAX_VOLTS == 4.1


def test_rexzb_111_entity_metadata():
    """Test REXZB-111 exposes battery and AC power entities."""
    quirk = _get_range_extender_quirk_entry("REXZB-111")

    entity_map = {
        entity_metadata.unique_id_suffix: entity_metadata
        for entity_metadata in quirk.entity_metadata
    }

    assert "ac_power" in entity_map
    assert "battery" in entity_map
    assert "battery_percentage" in entity_map

    power_entity = entity_map["ac_power"]
    assert power_entity.entity_type is EntityType.DIAGNOSTIC
    assert power_entity.device_class == BinarySensorDeviceClass.POWER
    assert power_entity.cluster_id == IasZone.cluster_id
    assert power_entity.endpoint_id == 37
    assert power_entity.fallback_name == "AC Power"

    battery_binary = entity_map["battery"]
    assert battery_binary.entity_type is EntityType.DIAGNOSTIC
    assert battery_binary.device_class == BinarySensorDeviceClass.BATTERY
    assert battery_binary.cluster_id == IasZone.cluster_id
    assert battery_binary.endpoint_id == 37

    battery_percentage = entity_map["battery_percentage"]
    assert battery_percentage.entity_type is EntityType.DIAGNOSTIC
    assert battery_percentage.unit == PERCENTAGE
    assert battery_percentage.divisor == 2
    assert battery_percentage.cluster_id == PowerConfiguration.cluster_id
    assert battery_percentage.endpoint_id == 37
    assert battery_percentage.fallback_name == "Battery Percentage"


def test_rexzb_110_minimal_quirk():
    """Test REXZB-110 registers a minimal quirk with no entities."""
    quirk = _get_range_extender_quirk_entry("REXZB-110")

    assert quirk.entity_metadata == ()

def test_power_binary_sensor_attribute_converter(zigpy_device_from_v2_quirk):
    """Test power entity converter with inverted IAS AC_mains bit semantics."""
    device = zigpy_device_from_v2_quirk(
        manufacturer="frient A/S",
        model="REXZB-111",
        endpoint_ids=[37],
        cluster_ids={
            37: {
                PowerConfiguration.cluster_id: ClusterType.Server,
                IasZone.cluster_id: ClusterType.Server,
            }
        },
    )

    metadata = device.exposes_metadata[(37, IasZone.cluster_id, ClusterType.Server)]
    power_meta = next(
        entity for entity in metadata if entity.unique_id_suffix == "ac_power"
    )
    converter = power_meta.attribute_converter

    # IAS AC_mains bit set indicates battery operation, so AC power must be False.
    assert converter(IasZone.ZoneStatus.AC_mains) is False
    # IAS AC_mains bit unset indicates mains power, so AC power must be True.
    assert converter(IasZone.ZoneStatus.Alarm_1) is True
    # IAS AC_mains bit still wins when combined with other zone status flags.
    assert converter(IasZone.ZoneStatus.AC_mains | IasZone.ZoneStatus.Alarm_1) is False
