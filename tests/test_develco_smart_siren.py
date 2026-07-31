"""Tests for Develco smart siren quirk."""

from zha.quirks import DEVICE_REGISTRY as ZHA_DEVICE_REGISTRY
from zigpy.zcl import ClusterType
from zigpy.zcl.clusters.general import PowerConfiguration
from zigpy.zcl.clusters.security import IasWd, IasZone

import zhaquirks

zhaquirks.setup()


async def test_siren_metadata_entities_present(zigpy_device_from_v2_quirk):
    """Test v2 metadata exposes expected entities."""
    device = zigpy_device_from_v2_quirk(
        manufacturer="frient A/S",
        model="SIRZB-110",
        endpoint_ids=[43],
        cluster_ids={
            43: {
                IasWd.cluster_id: ClusterType.Server,
                IasZone.cluster_id: ClusterType.Server,
                PowerConfiguration.cluster_id: ClusterType.Server,
            }
        },
    )
    entry = ZHA_DEVICE_REGISTRY.match_entry(device)
    assert entry is not None

    translation_keys = {
        m.translation_key
        for m in entry.zha_device_factory.quirk_definition.entity_metadata
        if m.translation_key is not None
    }

    assert "max_duration" in translation_keys


async def test_power_binary_sensor_attribute_converter(zigpy_device_from_v2_quirk):
    """Test power entity converter with inverted IAS AC_mains bit semantics."""
    device = zigpy_device_from_v2_quirk(
        manufacturer="frient A/S",
        model="SIRZB-110",
        endpoint_ids=[43],
        cluster_ids={
            43: {
                IasWd.cluster_id: ClusterType.Server,
                IasZone.cluster_id: ClusterType.Server,
            }
        },
    )
    entry = ZHA_DEVICE_REGISTRY.match_entry(device)
    assert entry is not None

    power_meta = next(
        m
        for m in entry.zha_device_factory.quirk_definition.entity_metadata
        if m.unique_id_suffix == "power"
    )
    converter = power_meta.attribute_converter

    # IAS AC_mains bit set indicates mains fault, so AC power must be False.
    assert converter(IasZone.ZoneStatus.AC_mains) is False
    # IAS AC_mains bit unset indicates mains power, so AC power must be True.
    assert converter(IasZone.ZoneStatus.Alarm_1) is True
    # IAS AC_mains bit still wins when combined with other zone status flags.
    assert converter(IasZone.ZoneStatus.AC_mains | IasZone.ZoneStatus.Alarm_1) is False
