"""Tests for Zemismart ZPS-Z1 Tuya quirk."""

from zigpy.zcl import foundation

from zhaquirks.tuya.TS0601_TZE284_ft7qqpx3 import (
    AutoCalibrationCmd,
    SensitivityPreset,
    ZpsZ1ManufCluster,
)

DP_AI_SELF_LEARNING = 103
DP_SENSITIVITY_PRESET = 112
DP_ZONE_MAP = 117
DP_ENERGY_THRESHOLD = 124
DP_ENERGY_STREAMING = 104

DT_RAW = 0x00
DT_ENUM = 0x04


def _dp_frame(dp: int, dp_type: int, payload: bytes) -> bytes:
    """Build a Tuya get_data frame containing one datapoint."""
    return (
        b"\x09\x4c\x01\x00"
        + bytes([len(payload) + 4, dp, dp_type])
        + len(payload).to_bytes(2, "big")
        + payload
    )


async def test_zps_z1_auto_calibration_status(zigpy_device_from_v2_quirk):
    """Test DP103 auto calibration status updates."""
    device = zigpy_device_from_v2_quirk("_TZE284_ft7qqpx3", "TS0601")
    cluster = device.endpoints[1].tuya_manufacturer

    assert isinstance(cluster, ZpsZ1ManufCluster)

    hdr, data = cluster.deserialize(_dp_frame(DP_AI_SELF_LEARNING, DT_ENUM, b"\x02"))
    status = cluster.handle_get_data(data.data)

    assert status == foundation.Status.SUCCESS

    success, _ = await cluster.read_attributes(
        ("auto_calibration_status", "auto_calibration")
    )

    assert success["auto_calibration_status"] == "learning"
    assert success["auto_calibration"] == AutoCalibrationCmd.standby


async def test_zps_z1_sensitivity_preset(zigpy_device_from_v2_quirk):
    """Test DP112 sensitivity preset updates."""
    device = zigpy_device_from_v2_quirk("_TZE284_ft7qqpx3", "TS0601")
    cluster = device.endpoints[1].tuya_manufacturer

    hdr, data = cluster.deserialize(_dp_frame(DP_SENSITIVITY_PRESET, DT_ENUM, b"\x01"))
    status = cluster.handle_get_data(data.data)

    assert status == foundation.Status.SUCCESS

    success, _ = await cluster.read_attributes(("sensitivity_preset",))
    assert success["sensitivity_preset"] == SensitivityPreset.medium


async def test_zps_z1_zone_map(zigpy_device_from_v2_quirk):
    """Test DP117 zone map updates zone active attributes."""
    device = zigpy_device_from_v2_quirk("_TZE284_ft7qqpx3", "TS0601")
    cluster = device.endpoints[1].tuya_manufacturer

    payload = b"\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00"
    hdr, data = cluster.deserialize(_dp_frame(DP_ZONE_MAP, DT_RAW, payload))
    status = cluster.handle_get_data(data.data)

    assert status == foundation.Status.SUCCESS

    success, _ = await cluster.read_attributes(("zone_1_active", "zone_7_active"))
    assert success["zone_1_active"] is True
    assert success["zone_7_active"] is False


async def test_zps_z1_energy_thresholds(zigpy_device_from_v2_quirk):
    """Test DP124 threshold decoding."""
    device = zigpy_device_from_v2_quirk("_TZE284_ft7qqpx3", "TS0601")
    cluster = device.endpoints[1].tuya_manufacturer

    payload = bytes([42, 38, 26, 22, 22, 18, 18, 18, 18, 18])
    payload += bytes([28, 23, 20, 13, 13, 11, 11, 11, 11, 11])

    hdr, data = cluster.deserialize(_dp_frame(DP_ENERGY_THRESHOLD, DT_RAW, payload))
    status = cluster.handle_get_data(data.data)

    assert status == foundation.Status.SUCCESS

    success, _ = await cluster.read_attributes(
        ("zone_1_motion_threshold", "zone_1_presence_threshold")
    )

    assert success["zone_1_motion_threshold"] == 16
    assert success["zone_1_presence_threshold"] == 11

