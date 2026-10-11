"""Tests for Tuya quirks."""

import asyncio
from unittest import mock

import pytest
from zha.quirks import DEVICE_REGISTRY
import zigpy.types as t
from zigpy.zcl import ClusterType, foundation
from zigpy.zcl.clusters.measurement import IlluminanceMeasurement, OccupancySensing
from zigpy.zcl.clusters.security import IasZone

from tests.common import ClusterListener
import zhaquirks
from zhaquirks.builder.metadata import ZCLEnumMetadata
import zhaquirks.tuya
from zhaquirks.tuya.mcu import TuyaMCUCluster
from zhaquirks.tuya.tuya_motion import (
    HobeianZG204ZIasZone,
    HobeianZG204ZKeepTime,
    HobeianZG204ZSensitivity,
)

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
    "model,manuf,illum_msg,exp_value",
    [
        ("_TZE204_1youk3hj", "TS0601", b"\tL\x01\x00\x05\x66\x04\x00\x01\x00", 10),
        ("_TZE204_1youk3hj", "TS0601", b"\tL\x01\x00\x05\x66\x04\x00\x01\x01", 20),
        ("_TZE204_1youk3hj", "TS0601", b"\tL\x01\x00\x05\x66\x04\x00\x01\x02", 50),
        ("_TZE204_1youk3hj", "TS0601", b"\tL\x01\x00\x05\x66\x04\x00\x01\x03", 100),
    ],
)
async def test_tuya_motion_quirk_enum_illum(
    zigpy_device_from_v2_quirk, model, manuf, illum_msg, exp_value
):
    """Test Tuya Motion Quirks using enum illumination."""
    quirked_device = zigpy_device_from_v2_quirk(model, manuf)
    ep = quirked_device.endpoints[1]

    assert ep.illuminance is not None
    assert isinstance(ep.illuminance, IlluminanceMeasurement)

    illum_listener = ClusterListener(ep.illuminance)

    hdr, data = ep.tuya_manufacturer.deserialize(illum_msg)
    status = ep.tuya_manufacturer.handle_get_data(data.data)

    assert status == foundation.Status.SUCCESS

    zcl_illum_id = IlluminanceMeasurement.AttributeDefs.measured_value.id

    assert len(illum_listener.attribute_updates) == 1
    assert illum_listener.attribute_updates[0][0] == zcl_illum_id
    assert illum_listener.attribute_updates[0][1] == exp_value


def test_hobeian_zg204z_quirk(zigpy_device_from_v2_quirk):
    """Test HOBEIAN ZG-204Z exposes its IAS zone settings and hides occupancy."""
    quirked_device = zigpy_device_from_v2_quirk(
        "HOBEIAN",
        "ZG-204Z",
        cluster_ids={
            1: {
                IasZone.cluster_id: ClusterType.Server,
                OccupancySensing.cluster_id: ClusterType.Server,
            }
        },
    )

    assert isinstance(quirked_device.endpoints[1].ias_zone, HobeianZG204ZIasZone)

    definition = DEVICE_REGISTRY.match_entry(
        quirked_device
    ).zha_device_factory.quirk_definition

    enums = {
        metadata.attribute_name: metadata
        for metadata in definition.entity_metadata
        if isinstance(metadata, ZCLEnumMetadata)
    }
    assert enums["current_zone_sensitivity_level"].enum is HobeianZG204ZSensitivity
    assert enums["keep_time"].enum is HobeianZG204ZKeepTime
    assert {m.cluster_id for m in enums.values()} == {IasZone.cluster_id}

    assert [
        (m.endpoint_id, m.cluster_id) for m in definition.disabled_default_entities
    ] == [(1, OccupancySensing.cluster_id)]


@pytest.mark.parametrize(
    "attribute,value",
    [
        ("current_zone_sensitivity_level", HobeianZG204ZSensitivity.Low),
        ("keep_time", HobeianZG204ZKeepTime.For_120_seconds),
    ],
)
async def test_hobeian_zg204z_writes(zigpy_device_from_v2_quirk, attribute, value):
    """Test HOBEIAN ZG-204Z settings are written as uint8, without a manufacturer code."""
    quirked_device = zigpy_device_from_v2_quirk(
        "HOBEIAN",
        "ZG-204Z",
        cluster_ids={1: {IasZone.cluster_id: ClusterType.Server}},
    )
    ias_zone = quirked_device.endpoints[1].ias_zone

    assert ias_zone.find_attribute(attribute).type is t.uint8_t

    with mock.patch.object(
        ias_zone,
        "request",
        new=mock.AsyncMock(
            return_value=[
                [foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)]
            ]
        ),
    ) as request:
        await ias_zone.write_attributes({attribute: value})

    assert request.call_args.kwargs["manufacturer"] is None
