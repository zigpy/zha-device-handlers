"""Tests for the HOBEIAN ZG-301Z-2CH 2-channel switch quirk."""

from unittest import mock

import pytest
from zha.application import EntityPlatform, EntityType
from zha.quirks import DEVICE_REGISTRY
from zigpy.profiles import zha
from zigpy.zcl import ClusterType, foundation
from zigpy.zcl.clusters.general import (
    Basic,
    Groups,
    Identify,
    OnOff,
    OnOffConfiguration,
    Ota,
    PowerConfiguration,
    Scenes,
    StartUpOnOff,
    Time,
)

import zhaquirks
from zhaquirks.builder.metadata import ZCLEnumMetadata
from zhaquirks.tuya import (
    TUYA_CLUSTER_E000_ID,
    TUYA_CLUSTER_E001_ID,
    ExternalSwitchType,
    TuyaZBExternalSwitchTypeCluster,
)
import zhaquirks.tuya.hobeian_zg301z_2ch
from zhaquirks.tuya.hobeian_zg301z_2ch import (
    HobeianCH1OnOff,
    HobeianCH2OnOff,
    HobeianExternalSwitchType,
)

zhaquirks.setup()

EP1_CLUSTERS = {
    Basic.cluster_id: ClusterType.Server,
    PowerConfiguration.cluster_id: ClusterType.Server,
    Identify.cluster_id: ClusterType.Server,
    Groups.cluster_id: ClusterType.Server,
    Scenes.cluster_id: ClusterType.Server,
    OnOff.cluster_id: ClusterType.Server,
    OnOffConfiguration.cluster_id: ClusterType.Server,
    TUYA_CLUSTER_E000_ID: ClusterType.Server,
    0xE002: ClusterType.Server,
    0xEE00: ClusterType.Server,
    0xEF00: ClusterType.Server,
}

EP2_CLUSTERS = {
    Basic.cluster_id: ClusterType.Server,
    Identify.cluster_id: ClusterType.Server,
    Groups.cluster_id: ClusterType.Server,
    Scenes.cluster_id: ClusterType.Server,
    OnOff.cluster_id: ClusterType.Server,
}


@pytest.fixture
def device(zigpy_device_from_v2_quirk):
    """Build the quirked HOBEIAN device with the device's reported clusters."""
    return zigpy_device_from_v2_quirk(
        "HOBEIAN",
        "ZG-301Z-2CH",
        cluster_ids={
            1: {
                **EP1_CLUSTERS,
                Time.cluster_id: ClusterType.Client,
                Ota.cluster_id: ClusterType.Client,
            },
            2: EP2_CLUSTERS,
        },
    )


def test_quirk_matches(device):
    """Test the quirk matches the device and is the v2 HOBEIAN quirk."""
    entry = DEVICE_REGISTRY.match_entry(device)
    assert entry is not None
    assert entry.source.file.endswith("hobeian_zg301z_2ch.py")


def test_channel_onoff_clusters(device):
    """Test both channels replaced with the per-channel OnOff clusters."""
    assert isinstance(device.endpoints[1].on_off, HobeianCH1OnOff)
    assert isinstance(device.endpoints[2].on_off, HobeianCH2OnOff)


def test_switch_type_cluster_present(device):
    """Test the 0xE001 switch type cluster is added to endpoint 1."""
    assert isinstance(
        device.endpoints[1].in_clusters[TUYA_CLUSTER_E001_ID],
        HobeianExternalSwitchType,
    )
    assert (
        TuyaZBExternalSwitchTypeCluster.AttributeDefs.external_switch_type.id == 0xD030
    )


def test_switch_type_select_entity(device):
    """Test the quirk exposes the external switch type as a config select."""
    entry = DEVICE_REGISTRY.match_entry(device)
    quirk_definition = entry.zha_device_factory.quirk_definition

    enum_metadata = [
        m for m in quirk_definition.entity_metadata if isinstance(m, ZCLEnumMetadata)
    ]
    assert enum_metadata, "no enum metadata declared"
    assert any(
        m.attribute_name == "external_switch_type"
        and m.enum == ExternalSwitchType
        and m.cluster_id == TUYA_CLUSTER_E001_ID
        and m.endpoint_id == 1
        and m.entity_platform == EntityPlatform.SELECT
        and m.entity_type == EntityType.CONFIG
        for m in enum_metadata
    )


@pytest.mark.parametrize(
    ("endpoint_id", "channel"),
    [(1, "CH1"), (2, "CH2")],
)
def test_power_on_behavior_select_entity(device, endpoint_id, channel):
    """Test the per-channel power-on behavior selects replace the native ones."""
    entry = DEVICE_REGISTRY.match_entry(device)
    quirk_definition = entry.zha_device_factory.quirk_definition

    enum_metadata = [
        m for m in quirk_definition.entity_metadata if isinstance(m, ZCLEnumMetadata)
    ]
    matching = [
        m
        for m in enum_metadata
        if m.attribute_name == OnOff.AttributeDefs.start_up_on_off.name
        and m.endpoint_id == endpoint_id
    ]
    assert len(matching) == 1
    assert matching[0].enum == StartUpOnOff
    assert matching[0].cluster_id == OnOff.cluster_id
    assert matching[0].entity_platform == EntityPlatform.SELECT
    assert matching[0].entity_type == EntityType.CONFIG
    assert matching[0].unique_id_suffix == "pon_behavior"
    assert matching[0].translation_key == "power_on_behavior_ch"
    assert matching[0].translation_placeholders == {"channel": channel}
    assert matching[0].fallback_name == f"Power-on behavior ({channel})"

    # The identical duplicates (ZHA-native StartupOnOffSelectEntity) are suppressed
    disabled = [
        f
        for f in quirk_definition.disabled_default_entities
        if f.unique_id_suffix == "StartUpOnOff"
        and f.cluster_id == OnOff.cluster_id
        and f.endpoint_id == endpoint_id
    ]
    assert len(disabled) == 1


async def test_switch_entities(zigpy_device_from_v2_quirk):
    """Test both channels present as ON_OFF_SWITCH device types."""
    device = zigpy_device_from_v2_quirk(
        "HOBEIAN",
        "ZG-301Z-2CH",
        cluster_ids={
            1: EP1_CLUSTERS,
            2: EP2_CLUSTERS,
        },
    )

    assert device.endpoints[1].device_type == zha.DeviceType.ON_OFF_SWITCH
    assert device.endpoints[2].device_type == zha.DeviceType.ON_OFF_SWITCH


async def test_spell_casts_read_attribute(device):
    """Test the attribute read spell is cast during configuration."""
    with mock.patch(
        "zigpy.zcl.Cluster.request",
        mock.AsyncMock(return_value=(foundation.Status.SUCCESS, "done")),
    ) as request_mock:
        await device.apply_custom_configuration()

    read_calls = [
        c
        for c in request_mock.call_args_list
        if c.args[1] == foundation.GeneralCommand.Read_Attributes
    ]
    assert read_calls, "attribute read spell was not cast"
    assert read_calls[0].args[3] == [4, 0, 1, 5, 7, 65534]
