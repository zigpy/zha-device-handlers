"""Tests for Wenzhi quirks."""

from unittest import mock

import pytest
from zigpy.zcl import ClusterType, foundation
from zigpy.zcl.clusters.general import Basic, GreenPowerProxy, Groups, Ota, Scenes, Time
from zigpy.zcl.clusters.security import IasZone

from zhaquirks.device import CustomZigpyDevice
from zhaquirks.tuya import BaseEnchantedDevice, TuyaNewManufCluster
import zhaquirks.wenzhi.mtd085_motion

zhaquirks.setup()


@pytest.mark.parametrize("manufacturer", ["_TZ321C_fkzihax8", "_TZ321C_4slreunp"])
async def test_mtd085_magic_packet(zigpy_device_from_v2_quirk, manufacturer):
    """Initialize both TS0225 variants with one spell read and preserve IAS Zone."""
    device = zigpy_device_from_v2_quirk(
        manufacturer,
        "TS0225",
        cluster_ids={
            1: {
                Groups.cluster_id: ClusterType.Server,
                Scenes.cluster_id: ClusterType.Server,
                IasZone.cluster_id: ClusterType.Server,
                Time.cluster_id: ClusterType.Client,
                Ota.cluster_id: ClusterType.Client,
            },
            242: {GreenPowerProxy.cluster_id: ClusterType.Client},
        },
    )

    assert isinstance(device, CustomZigpyDevice)
    assert isinstance(device, BaseEnchantedDevice)
    assert device.manufacturer == manufacturer
    assert device.model == "TS0225"
    assert set(device.endpoints) == {0, 1, 242}
    ep = device.endpoints[1]
    assert set(ep.in_clusters) == {
        Basic.cluster_id,
        Groups.cluster_id,
        Scenes.cluster_id,
        IasZone.cluster_id,
    }
    assert set(ep.out_clusters) == {Time.cluster_id, Ota.cluster_id}
    assert type(ep.ias_zone) is IasZone
    assert TuyaNewManufCluster.cluster_id not in ep.in_clusters
    assert not device.endpoints[242].in_clusters
    assert set(device.endpoints[242].out_clusters) == {GreenPowerProxy.cluster_id}

    with mock.patch.object(
        ep.basic,
        "request",
        mock.AsyncMock(return_value=(foundation.Status.SUCCESS, "done")),
    ) as request:
        await device.apply_custom_configuration()

    # Tuya accepts the spell only as one combined read of all six attributes.
    request.assert_awaited_once()
    assert request.call_args.args[0] is True  # General ZCL command.
    assert request.call_args.args[1] == foundation.GeneralCommand.Read_Attributes
    assert request.call_args.args[3] == [
        Basic.AttributeDefs.manufacturer.id,
        Basic.AttributeDefs.zcl_version.id,
        Basic.AttributeDefs.app_version.id,
        Basic.AttributeDefs.model.id,
        Basic.AttributeDefs.power_source.id,
        0xFFFE,  # Tuya-specific attribute required by the spell.
    ]
