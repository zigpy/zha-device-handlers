"""Tests for Zemismart ZPS-Z1 Tuya quirk."""

from zigpy.zcl import foundation

from zhaquirks.tuya.TS0601_TZE284_ft7qqpx3 import (
    AutoCalibrationCmd,
    PresenceState,
    SensitivityPreset,
    ZpsZ1ManufCluster,
)

DP_PRESENCE_STATE = 1
DP_DETECTION_RANGE = 2
DP_ILLUMINANCE = 101
DP_ENERGY_VALUE = 102
DP_AI_SELF_LEARNING = 103
DP_ENERGY_STREAMING = 104
DP_HEART = 105
DP_SENSITIVITY_PRESET = 112
DP_ZONE_MAP = 117
DP_NO_PERSON_TIME = 119
DP_INDICATOR = 123
DP_ENERGY_THRESHOLD = 124

DT_RAW = 0x00
DT_BOOL = 0x01
DT_VALUE = 0x02
DT_ENUM = 0x04


def _dp_frame(dp: int, dp_type: int, payload: bytes) -> bytes:
    """Build a Tuya get_data frame containing one datapoint."""
    return (
        b"\x09\x4c\x01\x00"
        + bytes([len(payload) + 4, dp, dp_type])
        + len(payload).to_bytes(2, "big")
        + payload
    )


def _value_payload(value: int) -> bytes:
    """Build a Tuya value payload."""
    return value.to_bytes(4, "big")


async def test_zps_z1_presence_state(zigpy_device_from_v2_quirk):
    """Test DP1 presence state updates."""
    device = zigpy_device_from_v2_quirk("_TZE284_ft7qqpx3", "TS0601")
    cluster = device.endpoints[1].tuya_manufacturer

    assert isinstance(cluster, ZpsZ1ManufCluster)

    hdr, data = cluster.deserialize(_dp_frame(DP_PRESENCE_STATE, DT_ENUM, b"\x02"))
    status = cluster.handle_get_data(data.data)

    assert status == foundation.Status.SUCCESS

    success, _ = await cluster.read_attributes(("presence_state",))
    assert success["presence_state"] == PresenceState.sensor_close


async def test_zps_z1_detection_range(zigpy_device_from_v2_quirk):
    """Test DP2 detection range updates."""
    device = zigpy_device_from_v2_quirk("_TZE284_ft7qqpx3", "TS0601")
    cluster = device.endpoints[1].tuya_manufacturer

    hdr, data = cluster.deserialize(
        _dp_frame(DP_DETECTION_RANGE, DT_VALUE, _value_payload(300))
    )
    status = cluster.handle_get_data(data.data)

    assert status == foundation.Status.SUCCESS

    success, _ = await cluster.read_attributes(("detection_range",))
    assert success["detection_range"] == 300


async def test_zps_z1_illuminance(zigpy_device_from_v2_quirk):
    """Test DP101 illuminance updates."""
    device = zigpy_device_from_v2_quirk("_TZE284_ft7qqpx3", "TS0601")
    cluster = device.endpoints[1].tuya_manufacturer

    hdr, data = cluster.deserialize(
        _dp_frame(DP_ILLUMINANCE, DT_VALUE, _value_payload(47))
    )
    status = cluster.handle_get_data(data.data)

    assert status == foundation.Status.SUCCESS

    success, _ = await cluster.read_attributes(("illuminance",))
    assert success["illuminance"] == 47


async def test_zps_z1_energy_values(zigpy_device_from_v2_quirk):
    """Test DP102 per-zone energy decoding."""
    device = zigpy_device_from_v2_quirk("_TZE284_ft7qqpx3", "TS0601")
    cluster = device.endpoints[1].tuya_manufacturer

    payload = bytes([255, 0, 128, 64, 32, 16, 8, 4, 2, 1])
    payload += bytes([128, 255, 0, 64, 32, 16, 8, 4, 2, 1])

    hdr, data = cluster.deserialize(_dp_frame(DP_ENERGY_VALUE, DT_RAW, payload))
    status = cluster.handle_get_data(data.data)

    assert status == foundation.Status.SUCCESS

    success, _ = await cluster.read_attributes(
        (
            "zone_1_motion_energy",
            "zone_2_motion_energy",
            "zone_1_presence_energy",
            "zone_2_presence_energy",
        )
    )

    assert success["zone_1_motion_energy"] == 100
    assert success["zone_2_motion_energy"] == 0
    assert success["zone_1_presence_energy"] == 50
    assert success["zone_2_presence_energy"] == 100


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


async def test_zps_z1_auto_calibration_terminal_status(zigpy_device_from_v2_quirk):
    """Test DP103 terminal auto calibration status resets the command select."""
    device = zigpy_device_from_v2_quirk("_TZE284_ft7qqpx3", "TS0601")
    cluster = device.endpoints[1].tuya_manufacturer

    hdr, data = cluster.deserialize(_dp_frame(DP_AI_SELF_LEARNING, DT_ENUM, b"\x03"))
    status = cluster.handle_get_data(data.data)

    assert status == foundation.Status.SUCCESS

    success, _ = await cluster.read_attributes(
        ("auto_calibration_status", "auto_calibration")
    )

    assert success["auto_calibration_status"] == "success"
    assert success["auto_calibration"] == AutoCalibrationCmd.standby


async def test_zps_z1_energy_streaming(zigpy_device_from_v2_quirk):
    """Test DP104 energy streaming updates."""
    device = zigpy_device_from_v2_quirk("_TZE284_ft7qqpx3", "TS0601")
    cluster = device.endpoints[1].tuya_manufacturer

    hdr, data = cluster.deserialize(_dp_frame(DP_ENERGY_STREAMING, DT_BOOL, b"\x01"))
    status = cluster.handle_get_data(data.data)

    assert status == foundation.Status.SUCCESS

    success, _ = await cluster.read_attributes(("energy_streaming",))
    assert success["energy_streaming"] is True


async def test_zps_z1_heart_datapoint_is_ignored(zigpy_device_from_v2_quirk):
    """Test DP105 heart datapoint is accepted and ignored."""
    device = zigpy_device_from_v2_quirk("_TZE284_ft7qqpx3", "TS0601")
    cluster = device.endpoints[1].tuya_manufacturer

    hdr, data = cluster.deserialize(_dp_frame(DP_HEART, DT_RAW, b"\x01"))
    status = cluster.handle_get_data(data.data)

    assert status == foundation.Status.SUCCESS


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


async def test_zps_z1_presence_clear_cooldown(zigpy_device_from_v2_quirk):
    """Test DP119 presence clear cooldown updates."""
    device = zigpy_device_from_v2_quirk("_TZE284_ft7qqpx3", "TS0601")
    cluster = device.endpoints[1].tuya_manufacturer

    hdr, data = cluster.deserialize(
        _dp_frame(DP_NO_PERSON_TIME, DT_VALUE, _value_payload(30))
    )
    status = cluster.handle_get_data(data.data)

    assert status == foundation.Status.SUCCESS

    success, _ = await cluster.read_attributes(("presence_clear_cooldown",))
    assert success["presence_clear_cooldown"] == 30


async def test_zps_z1_led_indicator(zigpy_device_from_v2_quirk):
    """Test DP123 LED indicator updates."""
    device = zigpy_device_from_v2_quirk("_TZE284_ft7qqpx3", "TS0601")
    cluster = device.endpoints[1].tuya_manufacturer

    hdr, data = cluster.deserialize(_dp_frame(DP_INDICATOR, DT_BOOL, b"\x01"))
    status = cluster.handle_get_data(data.data)

    assert status == foundation.Status.SUCCESS

    success, _ = await cluster.read_attributes(("led_indicator",))
    assert success["led_indicator"] is True


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


async def test_zps_z1_unknown_datapoint_returns_unsupported(
    zigpy_device_from_v2_quirk,
):
    """Test unknown datapoints return unsupported attribute."""
    device = zigpy_device_from_v2_quirk("_TZE284_ft7qqpx3", "TS0601")
    cluster = device.endpoints[1].tuya_manufacturer

    hdr, data = cluster.deserialize(_dp_frame(99, DT_RAW, b"\x01"))
    status = cluster.handle_get_data(data.data)

    assert status == foundation.Status.UNSUPPORTED_ATTRIBUTE
