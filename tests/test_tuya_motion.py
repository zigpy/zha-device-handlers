"""Tests for Tuya quirks."""

import asyncio
from unittest import mock

import pytest
from zigpy.zcl import foundation
from zigpy.zcl.clusters.measurement import (
    IlluminanceMeasurement,
    OccupancySensing,
    RelativeHumidity,
    TemperatureMeasurement,
)
from zigpy.zcl.clusters.security import IasZone

from tests.common import ClusterListener, wait_for_zigpy_tasks
import zhaquirks
import zhaquirks.tuya
from zhaquirks.tuya.mcu import TuyaMCUCluster

ZCL_TUYA_MOTION = b"\tL\x01\x00\x05\x01\x01\x00\x01\x01"  # DP 1
ZCL_TUYA_MOTION_V2 = b"\tL\x01\x00\x05\x65\x01\x00\x01\x01"  # DP 101
ZCL_TUYA_MOTION_V3 = b"\tL\x01\x00\x05\x03\x04\x00\x01\x02"  # DP 3, enum
ZCL_TUYA_MOTION_V4 = b"\tL\x01\x00\x05\x69\x01\x00\x01\x01"  # DP 105
ZCL_TUYA_MOTION_V5 = b"\tL\x01\x00\x05\x01\x01\x00\x01\x04"  # DP 1, motion is 0x04
ZCL_TUYA_MOTION_V6 = b"\tL\x01\x00\x05\x01\x04\x00\x01\x02"  # DP 1, enum
ZCL_TUYA_MOTION_V7 = b"\tL\x01\x00\x05\x01\x01\x00\x01\x00"  # DP 1, Inv
ZCL_TUYA_MOTION_V8 = b"\tL\x01\x00\x05\x65\x01\x00\x01\x00"  # DP 101, Inv
ZCL_TUYA_MOTION_V9 = b"\tL\x01\x00\x05\x68\x04\x00\x01\x01"  # DP 104, enum


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
        ("_TZE200_agumlajc", "TS0601", ZCL_TUYA_MOTION_V9),
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


async def test_mercator_combination_sensor(zigpy_device_from_v2_quirk):
    """Test Mercator Ikuu SSWMPIR-ZB readings and relay mode writes."""
    quirked_device = zigpy_device_from_v2_quirk("_TZE200_agumlajc", "TS0601")
    ep = quirked_device.endpoints[1]
    tuya_cluster = ep.tuya_manufacturer

    temp_listener = ClusterListener(ep.temperature)
    humidity_listener = ClusterListener(ep.humidity)
    illum_listener = ClusterListener(ep.illuminance)

    # Captured from a real device: 29.5 C (DP 1, x10), 61 % (DP 2), 6 lx (DP 101)
    for msg in (
        b"\tL\x01\x00\x05\x01\x02\x00\x04\x00\x00\x01\x27",
        b"\tL\x01\x00\x05\x02\x02\x00\x04\x00\x00\x00\x3d",
        b"\tL\x01\x00\x05\x65\x02\x00\x04\x00\x00\x00\x06",
    ):
        hdr, data = tuya_cluster.deserialize(msg)
        assert tuya_cluster.handle_get_data(data.data) == foundation.Status.SUCCESS

    assert temp_listener.attribute_updates == [
        (TemperatureMeasurement.AttributeDefs.measured_value.id, 2950)
    ]
    assert humidity_listener.attribute_updates == [
        (RelativeHumidity.AttributeDefs.measured_value.id, 6100)
    ]
    assert illum_listener.attribute_updates[0][0] == (
        IlluminanceMeasurement.AttributeDefs.measured_value.id
    )

    # Relay mode (DP 105) reported by the device
    hdr, data = tuya_cluster.deserialize(b"\tL\x01\x00\x05\x69\x04\x00\x01\x02")
    tuya_cluster.handle_get_data(data.data)
    assert tuya_cluster.get("relay_mode") == 2

    # Writing the relay mode sends DP 105 as an enum
    with mock.patch.object(
        tuya_cluster.endpoint, "request", return_value=foundation.Status.SUCCESS
    ) as m1:
        (status,) = await tuya_cluster.write_attributes({"relay_mode": 0x01})
        await wait_for_zigpy_tasks()
        assert m1.call_args.kwargs["data"].endswith(b"\x69\x04\x00\x01\x01")
        assert status == [
            foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)
        ]

        # Temperature offset (DP 108) is sent in tenths of a degree
        (status,) = await tuya_cluster.write_attributes({"temperature_offset": 10})
        await wait_for_zigpy_tasks()
        assert m1.call_args.kwargs["data"].endswith(b"\x6c\x02\x00\x04\x00\x00\x00\x0a")
