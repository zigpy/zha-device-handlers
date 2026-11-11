"""Tests for the SONOFF ZBMicro device."""

from unittest import mock

import pytest
from zha.quirks import DEVICE_REGISTRY
from zigpy.zcl import ClusterType, foundation

import zhaquirks
from zhaquirks.builder import EntityType
from zhaquirks.sonoff.zbmicro import SonoffCluster

zhaquirks.setup()

TURBO_MODE = SonoffCluster.AttributeDefs.turbo_mode


def _sonoff_cluster(zigpy_device_from_v2_quirk):
    """Return the quirked 0xFC11 cluster of a ZBMicro."""
    device = zigpy_device_from_v2_quirk(
        "SONOFF",
        "ZBMicro",
        cluster_ids={1: {SonoffCluster.cluster_id: ClusterType.Server}},
    )
    cluster = device.endpoints[1].in_clusters[SonoffCluster.cluster_id]
    assert isinstance(cluster, SonoffCluster)
    return cluster


def test_zbmicro_turbo_mode_entity(zigpy_device_from_v2_quirk):
    """The quirk adds a turbo mode switch that writes 20 for on and 9 for off."""
    cluster = _sonoff_cluster(zigpy_device_from_v2_quirk)

    entry = DEVICE_REGISTRY.match_entry(cluster.endpoint.device)
    (turbo_mode,) = entry.zha_device_factory.quirk_definition.entity_metadata
    assert turbo_mode.attribute_name == TURBO_MODE.name
    assert turbo_mode.cluster_id == SonoffCluster.cluster_id
    assert turbo_mode.endpoint_id == 1
    assert turbo_mode.on_value == 20
    assert turbo_mode.off_value == 9
    assert turbo_mode.entity_type == EntityType.CONFIG
    assert turbo_mode.translation_key == "turbo_mode"


@pytest.mark.parametrize("value", [20, 9], ids=["on", "off"])
async def test_zbmicro_turbo_mode_write_with_manufacturer_code(
    zigpy_device_from_v2_quirk, value
):
    """0x0012 is written with the manufacturer code, the device rejects it without."""
    cluster = _sonoff_cluster(zigpy_device_from_v2_quirk)

    write_mock = mock.AsyncMock(
        return_value=[
            [foundation.WriteAttributesStatusRecord(status=foundation.Status.SUCCESS)]
        ]
    )
    with mock.patch.object(cluster, "_write_attributes", write_mock):
        await cluster.write_attributes({TURBO_MODE.name: value})

    assert write_mock.await_count == 1
    assert write_mock.await_args.kwargs["manufacturer"] == 0x1286
    (record,) = write_mock.await_args.args[0]
    assert record.attrid == TURBO_MODE.id
    assert record.value.value == value
    assert cluster.get(TURBO_MODE.name) == value
