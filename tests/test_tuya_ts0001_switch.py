"""Tests for the Tuya TS0001 switch with power monitoring."""

from unittest import mock

import pytest
from zha.quirks import DEVICE_REGISTRY, TUYA_PLUG_ONOFF
from zigpy.zcl import ClusterType, foundation
from zigpy.zcl.clusters.general import Groups, Identify, OnOff, Ota, Scenes, Time
from zigpy.zcl.clusters.greenpower import GreenPowerProxy
from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement
from zigpy.zcl.clusters.smartenergy import Metering

from zhaquirks.builder.metadata import ExposesFeatureMetadata
import zhaquirks.tuya
from zhaquirks.tuya import (
    TUYA_CLUSTER_E000_ID,
    TUYA_CLUSTER_E001_ID,
    BaseEnchantedDevice,
    TuyaZBOnOffAttributeCluster,
)
import zhaquirks.tuya.ts0001_switch

zhaquirks.setup()

EP1_CLUSTERS = {
    Identify.cluster_id: ClusterType.Server,
    Groups.cluster_id: ClusterType.Server,
    Scenes.cluster_id: ClusterType.Server,
    OnOff.cluster_id: ClusterType.Server,
    Metering.cluster_id: ClusterType.Server,
    ElectricalMeasurement.cluster_id: ClusterType.Server,
    TUYA_CLUSTER_E001_ID: ClusterType.Server,
}


@pytest.mark.parametrize(
    "manufacturer,cluster_ids",
    [
        # same layout as ts000x.Switch_1G_Metering's signature (zha snapshot: kqvb5akv)
        (
            "_TZ3000_kqvb5akv",
            {
                1: {
                    **EP1_CLUSTERS,
                    TUYA_CLUSTER_E000_ID: ClusterType.Server,
                    Time.cluster_id: ClusterType.Client,
                    Ota.cluster_id: ClusterType.Client,
                },
                242: {GreenPowerProxy.cluster_id: ClusterType.Client},
            },
        ),
        # no Green Power endpoint (zha snapshot: mkhkxx1p)
        (
            "_TZ3000_mkhkxx1p",
            {
                1: {
                    **EP1_CLUSTERS,
                    TUYA_CLUSTER_E000_ID: ClusterType.Server,
                    Time.cluster_id: ClusterType.Client,
                    Ota.cluster_id: ClusterType.Client,
                }
            },
        ),
        # no 0xE000 cluster and no client clusters (zha snapshot: tgddllx4)
        ("_TZ3000_tgddllx4", {1: EP1_CLUSTERS}),
    ],
)
async def test_ts0001_switch_tuya_plug_parity(
    zigpy_device_from_v2_quirk, manufacturer, cluster_ids
):
    """Test the v2 quirk matches every layout and has the Tuya plug features + spell."""
    device = zigpy_device_from_v2_quirk(manufacturer, "TS0001", cluster_ids=cluster_ids)

    entry = DEVICE_REGISTRY.match_entry(device)
    assert entry is not None
    assert entry.source.file.endswith("ts0001_switch.py")
    assert ExposesFeatureMetadata(feature=TUYA_PLUG_ONOFF) in (
        entry.zha_device_factory.quirk_definition.exposes_features
    )

    assert isinstance(device.endpoints[1].on_off, TuyaZBOnOffAttributeCluster)
    assert isinstance(device, BaseEnchantedDevice)

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
