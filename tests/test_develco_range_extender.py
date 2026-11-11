"""Tests for Frient range extender quirks."""

from zha.quirks import DEVICE_REGISTRY as ZHA_DEVICE_REGISTRY
from zigpy.zcl import ClusterType
from zigpy.zcl.clusters.general import PowerConfiguration
from zigpy.zcl.clusters.security import IasZone

import zhaquirks
from zhaquirks.builder import PERCENTAGE, BinarySensorDeviceClass, EntityType
from zhaquirks.develco.range_extender import RangeExtenderPowerConfiguration

zhaquirks.setup()


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


async def test_rexzb_111_entity_metadata(zigpy_device_from_v2_quirk):
    """Test REXZB-111 exposes battery and AC power entities."""
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
    entry = ZHA_DEVICE_REGISTRY.match_entry(device)
    assert entry is not None

    entity_map = {
        m.unique_id_suffix: m
        for m in entry.zha_device_factory.quirk_definition.entity_metadata
    }

    assert "ac_power" in entity_map
    assert "battery" in entity_map
    assert "battery_percentage" in entity_map

    power_entity = entity_map["ac_power"]
    assert power_entity.entity_type is EntityType.DIAGNOSTIC
    assert power_entity.device_class == BinarySensorDeviceClass.POWER
    assert power_entity.cluster_id == IasZone.cluster_id
    assert power_entity.endpoint_id == 37
    assert power_entity.fallback_name == "AC power"

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
    assert battery_percentage.fallback_name == "Battery percentage"


async def test_power_binary_sensor_attribute_converter(zigpy_device_from_v2_quirk):
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
    entry = ZHA_DEVICE_REGISTRY.match_entry(device)
    assert entry is not None

    power_meta = next(
        m
        for m in entry.zha_device_factory.quirk_definition.entity_metadata
        if m.unique_id_suffix == "ac_power"
    )
    converter = power_meta.attribute_converter

    # IAS AC_mains bit set indicates mains fault, so AC power must be False.
    assert converter(IasZone.ZoneStatus.AC_mains) is False
    # IAS AC_mains bit unset indicates mains power, so AC power must be True.
    assert converter(IasZone.ZoneStatus.Alarm_1) is True
    # IAS AC_mains bit still wins when combined with other zone status flags.
    assert converter(IasZone.ZoneStatus.AC_mains | IasZone.ZoneStatus.Alarm_1) is False
