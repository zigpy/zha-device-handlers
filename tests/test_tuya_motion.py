"""Tests for Tuya quirks."""

import asyncio

import pytest
from zigpy.types import Bool
from zigpy.zcl import foundation
from zigpy.zcl.clusters.measurement import IlluminanceMeasurement, OccupancySensing
from zigpy.zcl.clusters.security import IasZone

from tests.common import ClusterListener
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

# ZG-204ZV configuration datapoint messages
ZCL_ZG204ZV_SENSITIVITY = (
    b"\tL\x01\x00\x05\x02\x02\x00\x04\x00\x00\x00\x0a"  # DP 2, sensitivity=10
)
ZCL_ZG204ZV_FADING_TIME = (
    b"\tL\x01\x00\x05\x66\x02\x00\x04\x00\x00\x00\x3c"  # DP 102, fading_time=60s
)
ZCL_ZG204ZV_HUMIDITY_OFFSET = (
    b"\tL\x01\x00\x05\x68\x02\x00\x04\x00\x00\x00\x05"  # DP 104, humidity_offset=5
)
ZCL_ZG204ZV_TEMP_OFFSET = (
    b"\tL\x01\x00\x05\x69\x02\x00\x04\x00\x00\x00\x0a"  # DP 105, temp_offset=10 (1.0°C)
)
ZCL_ZG204ZV_ILLUM_INTERVAL = (
    b"\tL\x01\x00\x05\x6b\x02\x00\x04\x00\x00\x00\x0a"  # DP 107, illum_interval=10min
)
ZCL_ZG204ZV_LED_ON = b"\tL\x01\x00\x05\x6c\x01\x00\x01\x01"  # DP 108, LED indicator ON
ZCL_ZG204ZV_LED_OFF = (
    b"\tL\x01\x00\x05\x6c\x01\x00\x01\x00"  # DP 108, LED indicator OFF
)
ZCL_ZG204ZV_TEMP_UNIT_C = b"\tL\x01\x00\x05\x6d\x04\x00\x01\x00"  # DP 109, Celsius
ZCL_ZG204ZV_TEMP_UNIT_F = b"\tL\x01\x00\x05\x6d\x04\x00\x01\x01"  # DP 109, Fahrenheit


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
        ("_TZE200_2aaelwxk", "TS0601", ZCL_TUYA_MOTION),
        ("_TZE200_kb5noeto", "TS0601", ZCL_TUYA_MOTION),
        ("_TZE204_ex3rcdha", "TS0601", ZCL_TUYA_MOTION_V8),
        ("HOBEIAN", "ZG-204ZV", ZCL_TUYA_MOTION),
        ("_TZE200_uli8wasj", "TS0601", ZCL_TUYA_MOTION),
        ("_TZE200_grgol3xp", "TS0601", ZCL_TUYA_MOTION),
        ("_TZE200_rhgsbacq", "TS0601", ZCL_TUYA_MOTION),
        ("_TZE200_y8jijhba", "TS0601", ZCL_TUYA_MOTION),
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


@pytest.mark.parametrize(
    "model,manuf",
    [
        ("HOBEIAN", "ZG-204ZV"),
        ("_TZE200_uli8wasj", "TS0601"),
        ("_TZE200_grgol3xp", "TS0601"),
        ("_TZE200_rhgsbacq", "TS0601"),
        ("_TZE200_y8jijhba", "TS0601"),
    ],
)
async def test_zg204zv_tuya_config_datapoints(zigpy_device_from_v2_quirk, model, manuf):
    """Test ZG-204ZV Tuya configuration datapoints.

    Note: ZG-204ZV reports sensor data (battery, temperature, humidity, illuminance)
    via standard Zigbee clusters (0x0001, 0x0402, 0x0405, 0x0400) natively.
    This test focuses on Tuya datapoints used for occupancy detection and device
    configuration (sensitivity, fading time, offsets, intervals, LED, temp unit).
    """
    quirked_device = zigpy_device_from_v2_quirk(model, manuf)
    ep = quirked_device.endpoints[1]

    assert ep.tuya_manufacturer is not None
    assert isinstance(ep.tuya_manufacturer, TuyaMCUCluster)

    tmcu_listener = ClusterListener(ep.tuya_manufacturer)
    assert len(tmcu_listener.attribute_updates) == 0

    # Test DP 2: motion_detection_sensitivity (0-19)
    hdr, data = ep.tuya_manufacturer.deserialize(ZCL_ZG204ZV_SENSITIVITY)
    status = ep.tuya_manufacturer.handle_get_data(data.data)
    assert status == foundation.Status.SUCCESS
    assert ep.tuya_manufacturer.get((0xEF << 8) | 2) == 10
    assert len(tmcu_listener.attribute_updates) == 1
    assert tmcu_listener.attribute_updates[0][0] == (0xEF << 8) | 2
    assert tmcu_listener.attribute_updates[0][1] == 10

    # Test DP 102: fading_time (0-28800 seconds)
    hdr, data = ep.tuya_manufacturer.deserialize(ZCL_ZG204ZV_FADING_TIME)
    status = ep.tuya_manufacturer.handle_get_data(data.data)
    assert status == foundation.Status.SUCCESS
    assert ep.tuya_manufacturer.get((0xEF << 8) | 102) == 60
    assert len(tmcu_listener.attribute_updates) == 2
    assert tmcu_listener.attribute_updates[1][0] == (0xEF << 8) | 102
    assert tmcu_listener.attribute_updates[1][1] == 60

    # Test DP 104: humidity_offset (-30 to 30)
    hdr, data = ep.tuya_manufacturer.deserialize(ZCL_ZG204ZV_HUMIDITY_OFFSET)
    status = ep.tuya_manufacturer.handle_get_data(data.data)
    assert status == foundation.Status.SUCCESS
    assert ep.tuya_manufacturer.get((0xEF << 8) | 104) == 5
    assert len(tmcu_listener.attribute_updates) == 3
    assert tmcu_listener.attribute_updates[2][0] == (0xEF << 8) | 104
    assert tmcu_listener.attribute_updates[2][1] == 5

    # Test DP 105: temperature_offset (-2.0 to 2.0°C, step 0.1, multiplier 0.1)
    hdr, data = ep.tuya_manufacturer.deserialize(ZCL_ZG204ZV_TEMP_OFFSET)
    status = ep.tuya_manufacturer.handle_get_data(data.data)
    assert status == foundation.Status.SUCCESS
    # Device sends raw value 10, which with multiplier 0.1 = 1.0°C
    assert ep.tuya_manufacturer.get((0xEF << 8) | 105) == 10
    assert len(tmcu_listener.attribute_updates) == 4
    assert tmcu_listener.attribute_updates[3][0] == (0xEF << 8) | 105
    assert tmcu_listener.attribute_updates[3][1] == 10

    # Test DP 107: illuminance_interval (1-720 minutes)
    hdr, data = ep.tuya_manufacturer.deserialize(ZCL_ZG204ZV_ILLUM_INTERVAL)
    status = ep.tuya_manufacturer.handle_get_data(data.data)
    assert status == foundation.Status.SUCCESS
    assert ep.tuya_manufacturer.get((0xEF << 8) | 107) == 10
    assert len(tmcu_listener.attribute_updates) == 5
    assert tmcu_listener.attribute_updates[4][0] == (0xEF << 8) | 107
    assert tmcu_listener.attribute_updates[4][1] == 10

    # Test DP 108: led_indicator (bool)
    hdr, data = ep.tuya_manufacturer.deserialize(ZCL_ZG204ZV_LED_ON)
    status = ep.tuya_manufacturer.handle_get_data(data.data)
    assert status == foundation.Status.SUCCESS
    assert ep.tuya_manufacturer.get((0xEF << 8) | 108) == 1
    assert len(tmcu_listener.attribute_updates) == 6
    assert tmcu_listener.attribute_updates[5][0] == (0xEF << 8) | 108
    assert tmcu_listener.attribute_updates[5][1] == Bool.true

    hdr, data = ep.tuya_manufacturer.deserialize(ZCL_ZG204ZV_LED_OFF)
    status = ep.tuya_manufacturer.handle_get_data(data.data)
    assert status == foundation.Status.SUCCESS
    assert ep.tuya_manufacturer.get((0xEF << 8) | 108) == 0
    assert len(tmcu_listener.attribute_updates) == 7
    assert tmcu_listener.attribute_updates[6][0] == (0xEF << 8) | 108
    assert tmcu_listener.attribute_updates[6][1] == Bool.false

    # Test DP 109: temperature_unit_convert (enum: 0=Celsius, 1=Fahrenheit)
    hdr, data = ep.tuya_manufacturer.deserialize(ZCL_ZG204ZV_TEMP_UNIT_C)
    status = ep.tuya_manufacturer.handle_get_data(data.data)
    assert status == foundation.Status.SUCCESS
    assert ep.tuya_manufacturer.get((0xEF << 8) | 109) == 0
    assert len(tmcu_listener.attribute_updates) == 8
    assert tmcu_listener.attribute_updates[7][0] == (0xEF << 8) | 109
    assert tmcu_listener.attribute_updates[7][1] == 0

    hdr, data = ep.tuya_manufacturer.deserialize(ZCL_ZG204ZV_TEMP_UNIT_F)
    status = ep.tuya_manufacturer.handle_get_data(data.data)
    assert status == foundation.Status.SUCCESS
    assert ep.tuya_manufacturer.get((0xEF << 8) | 109) == 1
    assert len(tmcu_listener.attribute_updates) == 9
    assert tmcu_listener.attribute_updates[8][0] == (0xEF << 8) | 109
    assert tmcu_listener.attribute_updates[8][1] == 1
