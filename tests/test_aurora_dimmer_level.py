"""Tests for the Aurora two-gang battery dimmer level control cluster."""

from unittest import mock

import pytest
import zigpy.types as t
from zigpy.zcl.clusters.general import LevelControl

from zhaquirks.aurora.aurora_dimmer import AuroraDimmerBatteryPowered


@pytest.mark.parametrize("cached", [False, True])
@pytest.mark.parametrize("endpoint_id", [1, 2])
async def test_current_level_report_ignored(
    zigpy_device_from_quirk, endpoint_id, cached
):
    """The constant current_level report (254) after each step is thrown away."""
    device = zigpy_device_from_quirk(AuroraDimmerBatteryPowered)
    cluster = device.endpoints[endpoint_id].in_clusters[LevelControl.cluster_id]
    if cached:
        # A value already in the attribute cache, as on an existing install
        cluster._attr_cache.set_value(LevelControl.AttributeDefs.current_level, 254)
    listener = mock.MagicMock()
    cluster.add_listener(listener)

    # Report_Attributes: current_level (0x0000), uint8 (0x20), value 254
    device.packet_received(
        t.ZigbeePacket(
            profile_id=260,
            cluster_id=LevelControl.cluster_id,
            src_ep=endpoint_id,
            dst_ep=1,
            data=t.SerializableBytes(b"\x18\x01\x0a\x00\x00\x20\xfe"),
        )
    )

    assert listener.zha_send_event.mock_calls == []
    assert cluster.get(LevelControl.AttributeDefs.current_level.name) == (
        254 if cached else None
    )

    # Other attributes still go through: on_level (0x0011), uint8, value 100
    device.packet_received(
        t.ZigbeePacket(
            profile_id=260,
            cluster_id=LevelControl.cluster_id,
            src_ep=endpoint_id,
            dst_ep=1,
            data=t.SerializableBytes(b"\x18\x02\x0a\x11\x00\x20\x64"),
        )
    )

    assert cluster.get(LevelControl.AttributeDefs.on_level.name) == 100
    assert len(listener.zha_send_event.mock_calls) == 1
    assert listener.zha_send_event.mock_calls[0].args[1]["value"] == 100
