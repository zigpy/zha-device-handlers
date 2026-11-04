"""Tests for Tuya quirks."""

import asyncio
from unittest import mock

import pytest
from zha.quirks import DEVICE_REGISTRY
from zigpy.zcl import foundation
from zigpy.zcl.clusters.measurement import IlluminanceMeasurement, OccupancySensing
from zigpy.zcl.clusters.security import IasZone

from tests.common import ClusterListener, wait_for_zigpy_tasks
import zhaquirks
from zhaquirks.builder import EntityPlatform
from zhaquirks.builder.metadata import ZCLEnumMetadata
import zhaquirks.tuya
from zhaquirks.tuya.mcu import TuyaMCUCluster
from zhaquirks.tuya.tuya_motion import TuyaMotionIlluminanceThreshold

ZCL_TUYA_MOTION = b"\tL\x01\x00\x05\x01\x01\x00\x01\x01"  # DP 1
ZCL_TUYA_MOTION_V2 = b"\tL\x01\x00\x05\x65\x01\x00\x01\x01"  # DP 101
ZCL_TUYA_MOTION_V3 = b"\tL\x01\x00\x05\x03\x04\x00\x01\x02"  # DP 3, enum
ZCL_TUYA_MOTION_V4 = b"\tL\x01\x00\x05\x69\x01\x00\x01\x01"  # DP 105
ZCL_TUYA_MOTION_V5 = b"\tL\x01\x00\x05\x01\x01\x00\x01\x04"  # DP 1, motion is 0x04
ZCL_TUYA_MOTION_V6 = b"\tL\x01\x00\x05\x01\x04\x00\x01\x02"  # DP 1, enum
ZCL_TUYA_MOTION_V7 = b"\tL\x01\x00\x05\x01\x01\x00\x01\x00"  # DP 1, Inv
ZCL_TUYA_MOTION_V8 = b"\tL\x01\x00\x05\x65\x01\x00\x01\x00"  # DP 101, Inv


zhaquirks.setup()


@pytest.mark.parametrize(
    "model,manuf,occ_msg",
    [
        ("_TZE200_ya4ft0w4", "TS0601", ZCL_TUYA_MOTION),
        ("_TZE204_ya4ft0w4", "TS0601", ZCL_TUYA_MOTION),
        ("_TZE200_7hfcudw5", "TS0601", ZCL_TUYA_MOTION_V2),
        ("_TZE200_ppuj1vem", "TS0601", ZCL_TUYA_MOTION_V2),
        ("_TZE200_ar0slwnd", "TS0601", ZCL_TUYA_MOTION),
        ("_TZE200_mrf6vtua", "TS0601", ZCL_TUYA_MOTION),
        ("_TZE200_sfiy5tfs", "TS0601", ZCL_TUYA_MOTION),
        ("_TZE204_sooucan5", "TS0601", ZCL_TUYA_MOTION),
        ("_TZE200_wukb7rhc", "TS0601", ZCL_TUYA_MOTION),
        ("_TZE204_qasjif9e", "TS0601", ZCL_TUYA_MOTION),
        ("_TZE200_ztc6ggyl", "TS0601", ZCL_TUYA_MOTION),
        ("_TZE204_ztc6ggyl", "TS0601", ZCL_TUYA_MOTION),
        ("_TZE204_ztqnh5cg", "TS0601", ZCL_TUYA_MOTION),
        ("_TZE204_sbyx0lm6", "TS0601", ZCL_TUYA_MOTION),
        ("_TZE204_clrdrnya", "TS0601", ZCL_TUYA_MOTION),
        ("_TZE204_dtzziy1e", "TS0601", ZCL_TUYA_MOTION),
        ("_TZE204_iaeejhvf", "TS0601", ZCL_TUYA_MOTION),
        ("_TZE204_mtoaryre", "TS0601", ZCL_TUYA_MOTION),
        ("_TZE200_mp902om5", "TS0601", ZCL_TUYA_MOTION),
        ("_TZE204_pfayrzcw", "TS0601", ZCL_TUYA_MOTION),
        ("_TZE284_4qznlkbu", "TS0601", ZCL_TUYA_MOTION),
        ("_TZE200_sbyx0lm6", "TS0601", ZCL_TUYA_MOTION),
        ("_TZE204_muvkrjr5", "TS0601", ZCL_TUYA_MOTION),
        ("_TZE204_kyhbrfyl", "TS0601", ZCL_TUYA_MOTION),
        ("_TZ6210_duv6fhwt", "TS0601", ZCL_TUYA_MOTION),
        ("_TZE204_1youk3hj", "TS0601", ZCL_TUYA_MOTION),
        ("_TZE284_1youk3hj", "TS0601", ZCL_TUYA_MOTION),
        ("_TZE28C1000000_1youk3hj", "TS0601", ZCL_TUYA_MOTION),
        ("_TZE200_3towulqd", "TS0601", ZCL_TUYA_MOTION_V7),
        ("_TZE200_1ibpyhdc", "TS0601", ZCL_TUYA_MOTION_V7),
        ("_TZE200_bh3n6gk8", "TS0601", ZCL_TUYA_MOTION_V7),
        ("_TZE200_ttcovulf", "TS0601", ZCL_TUYA_MOTION_V7),
        ("_TZE204_sxm7l9xa", "TS0601", ZCL_TUYA_MOTION_V4),
        ("_TZE204_e5m9c5hl", "TS0601", ZCL_TUYA_MOTION_V4),
        ("_TZE204_dapwryy7", "TS0601", ZCL_TUYA_MOTION_V6),
        ("_TZE204_uxllnywp", "TS0601", ZCL_TUYA_MOTION_V5),
        ("_TZE200_gjldowol", "TS0601", ZCL_TUYA_MOTION),
        ("_TZE200_2aaelwxk", "TS0225", ZCL_TUYA_MOTION),
        ("_TZE200_crq3r3la", "CK-BL702-MWS-01(7016)", ZCL_TUYA_MOTION),
        ("HOBEIAN", "CK-BL702-MWS-01(7016)", ZCL_TUYA_MOTION),
        ("_TZE200_2aaelwxk", "TS0601", ZCL_TUYA_MOTION),
        ("_TZE200_kb5noeto", "TS0601", ZCL_TUYA_MOTION),
        ("_TZE204_ex3rcdha", "TS0601", ZCL_TUYA_MOTION_V8),
    ],
)
async def test_tuya_motion_quirk_occ(zigpy_device_from_v2_quirk, model, manuf, occ_msg):
    """Test Tuya Motion Quirks using Occupancy cluster."""
    quirked_device = zigpy_device_from_v2_quirk(model, manuf)
    ep = quirked_device.endpoints[1]

    assert ep.tuya_manufacturer is not None
    assert isinstance(ep.tuya_manufacturer, TuyaMCUCluster)

    assert ep.occupancy is not None
    assert isinstance(ep.occupancy, OccupancySensing)

    occupancy_listener = ClusterListener(ep.occupancy)

    hdr, data = ep.tuya_manufacturer.deserialize(occ_msg)
    status = ep.tuya_manufacturer.handle_get_data(data.data)

    assert status == foundation.Status.SUCCESS

    zcl_occupancy_id = OccupancySensing.AttributeDefs.occupancy.id

    assert len(occupancy_listener.attribute_updates) == 1
    assert occupancy_listener.attribute_updates[0][0] == zcl_occupancy_id
    assert (
        occupancy_listener.attribute_updates[0][1]
        == OccupancySensing.Occupancy.Occupied
    )


@pytest.mark.parametrize(
    "model,manuf,occ_msg",
    [
        ("_TYST11_i5j6ifxj", "5j6ifxj", ZCL_TUYA_MOTION_V3),
        ("_TYST11_7hfcudw5", "hfcudw5", ZCL_TUYA_MOTION_V3),
    ],
)
@pytest.mark.asyncio
async def test_tuya_motion_quirk_ias(zigpy_device_from_v2_quirk, model, manuf, occ_msg):
    """Test Tuya Motion Quirks using IasZone cluster."""
    quirked_device = zigpy_device_from_v2_quirk(model, manuf)
    ep = quirked_device.endpoints[1]

    assert ep.tuya_manufacturer is not None
    assert isinstance(ep.tuya_manufacturer, TuyaMCUCluster)

    assert ep.ias_zone is not None
    assert isinstance(ep.ias_zone, IasZone)

    # lower reset_s of IasZone cluster
    ep.ias_zone.reset_s = 0

    ias_zone_listener = ClusterListener(ep.ias_zone)

    hdr, data = ep.tuya_manufacturer.deserialize(occ_msg)
    status = ep.tuya_manufacturer.handle_get_data(data.data)

    assert status == foundation.Status.SUCCESS

    zcl_zone_status_id = IasZone.AttributeDefs.zone_status.id

    # check that the zone status is set to alarm_1
    assert len(ias_zone_listener.attribute_updates) == 1
    assert ias_zone_listener.attribute_updates[0][0] == zcl_zone_status_id
    assert ias_zone_listener.attribute_updates[0][1] == IasZone.ZoneStatus.Alarm_1

    await asyncio.sleep(0.01)

    # check that the zone status is reset automatically
    assert len(ias_zone_listener.attribute_updates) == 2
    assert ias_zone_listener.attribute_updates[1][0] == zcl_zone_status_id
    assert ias_zone_listener.attribute_updates[1][1] == 0


@pytest.mark.parametrize(
    "manufacturer",
    ["_TZE204_1youk3hj", "_TZE284_1youk3hj", "_TZE28C1000000_1youk3hj"],
)
@pytest.mark.parametrize("threshold", list(TuyaMotionIlluminanceThreshold))
async def test_tuya_motion_illuminance_threshold(
    zigpy_device_from_v2_quirk, manufacturer, threshold
):
    """Test the NAS-PS10B2 illuminance threshold setting (DP 102)."""
    quirked_device = zigpy_device_from_v2_quirk(manufacturer, "TS0601")
    ep = quirked_device.endpoints[1]
    tuya_cluster = ep.tuya_manufacturer
    attr_id = tuya_cluster.attributes_by_name["illuminance_threshold"].id

    # DP 102 is a setting, no illuminance cluster is added for it
    assert IlluminanceMeasurement.cluster_id not in ep.in_clusters

    entry = DEVICE_REGISTRY.match_entry(quirked_device)
    metadata = {
        m.resolved_unique_id_suffix: m
        for m in entry.zha_device_factory.quirk_definition.entity_metadata
    }
    select = metadata["illuminance_threshold"]
    assert isinstance(select, ZCLEnumMetadata)
    assert select.entity_platform == EntityPlatform.SELECT
    assert select.enum is TuyaMotionIlluminanceThreshold

    tuya_listener = ClusterListener(tuya_cluster)

    msg = b"\tL\x01\x00\x05\x66\x04\x00\x01" + bytes([threshold.value])
    hdr, data = tuya_cluster.deserialize(msg)
    status = tuya_cluster.handle_get_data(data.data)

    assert status == foundation.Status.SUCCESS
    assert tuya_listener.attribute_updates == [(attr_id, threshold)]

    with mock.patch.object(
        tuya_cluster.endpoint, "request", return_value=foundation.Status.SUCCESS
    ) as m1:
        (status,) = await tuya_cluster.write_attributes(
            {"illuminance_threshold": threshold}
        )
        await wait_for_zigpy_tasks()

        assert m1.call_args.kwargs["data"] == (
            b"\x01\x01\x00\x00\x01\x66\x04\x00\x01" + bytes([threshold.value])
        )
        assert status == [
            foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)
        ]


@pytest.mark.parametrize(
    "manufacturer",
    ["_TZE204_1youk3hj", "_TZE284_1youk3hj", "_TZE28C1000000_1youk3hj"],
)
async def test_tuya_motion_fading_time_unset(zigpy_device_from_v2_quirk, manufacturer):
    """Test the NAS-PS10B2 fading time (DP 12) ignores the unset value."""
    quirked_device = zigpy_device_from_v2_quirk(manufacturer, "TS0601")
    tuya_cluster = quirked_device.endpoints[1].tuya_manufacturer

    entry = DEVICE_REGISTRY.match_entry(quirked_device)
    metadata = {
        m.resolved_unique_id_suffix: m
        for m in entry.zha_device_factory.quirk_definition.entity_metadata
    }
    number = metadata["fading_time"]
    assert number.entity_platform == EntityPlatform.NUMBER
    assert (number.min, number.max) == (3, 600)
    assert tuya_cluster.attributes_by_name["fading_time"].access == (
        foundation.ZCLAttributeAccess.Read | foundation.ZCLAttributeAccess.Write
    )

    def receive(raw: bytes) -> None:
        msg = b"\tL\x01\x00\x05\x0c\x02\x00\x04" + raw
        hdr, data = tuya_cluster.deserialize(msg)
        assert tuya_cluster.handle_get_data(data.data) == foundation.Status.SUCCESS

    receive(b"\x00\x00\x00\x05")
    assert tuya_cluster.get("fading_time") == 5

    # Sent by a device whose fading time was never set
    receive(b"\xff\xff\xff\x08")
    assert tuya_cluster.get("fading_time") is None

    for value in (3, 600):
        with mock.patch.object(
            tuya_cluster.endpoint, "request", return_value=foundation.Status.SUCCESS
        ) as m1:
            (status,) = await tuya_cluster.write_attributes({"fading_time": value})
            await wait_for_zigpy_tasks()

            # ZCL header and Tuya status/tsn first, then DP 12 as a 4 byte value
            assert m1.call_args.kwargs["data"][5:] == (
                b"\x0c\x02\x00\x04" + value.to_bytes(4, "big")
            )
            assert status == [
                foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)
            ]


@pytest.mark.asyncio
async def test_hobeian_zg204zl_config_dps(zigpy_device_from_v2_quirk):
    """Test the HOBEIAN ZG-204ZL configuration datapoints.

    Occupancy/battery/illuminance stay on the native clusters, so only the
    sensitivity/fading/interval datapoints are mapped by this quirk.
    """

    quirked = zigpy_device_from_v2_quirk("HOBEIAN", "ZG-204ZL")
    ep = quirked.endpoints[1]

    assert ep.tuya_manufacturer is not None
    assert isinstance(ep.tuya_manufacturer, TuyaMCUCluster)

    # DP 9 (enum): sensitivity 2 = High, DP 10 (enum): fading time 3 = 120 s
    for msg in (
        b"\tL\x01\x00\x05\x09\x04\x00\x01\x02",
        b"\tL\x01\x00\x05\x0a\x04\x00\x01\x03",
    ):
        hdr, data = ep.tuya_manufacturer.deserialize(msg)
        status = ep.tuya_manufacturer.handle_get_data(data.data)
        assert status == foundation.Status.SUCCESS

    assert ep.tuya_manufacturer.get("presence_sensitivity") == 2
    assert ep.tuya_manufacturer.get("fading_time") == 3
