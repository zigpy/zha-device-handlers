"""Tests for Tuya quirks."""

import pytest
from zigpy.zcl import foundation
from zigpy.zcl.clusters.measurement import OccupancySensing

from tests.common import ClusterListener
import zhaquirks
import zhaquirks.tuya
from zhaquirks.tuya.mcu import TuyaMCUCluster

ZCL_TUYA_MOTION = b"\tL\x01\x00\x05\x01\x01\x00\x01\x01"  # DP 1
ZCL_TUYA_MOTION_V2 = b"\tL\x01\x00\x05\x65\x01\x00\x01\x01"  # DP 101
ZCL_TUYA_MOTION_V3 = b"\tL\x01\x00\x05\x03\x04\x00\x01\x02"  # DP 3, enum


zhaquirks.setup()


@pytest.mark.parametrize(
    "model,manuf,occ_msg",
    [
        ("_TZE200_ya4ft0w4", "TS0601", ZCL_TUYA_MOTION),
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
        ("_TYST11_i5j6ifxj", "5j6ifxj", ZCL_TUYA_MOTION_V3),
        ("_TYST11_7hfcudw5", "hfcudw5", ZCL_TUYA_MOTION_V3),
    ],
)
async def test_tuya_motion_quirk(zigpy_device_from_v2_quirk, model, manuf, occ_msg):
    """Test Tuya Motion Quirks."""
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
