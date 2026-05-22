"""Tests for Zemismart ZPS-Z1 Tuya quirk."""

from asyncio import CancelledError
from unittest import mock

import pytest
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


async def test_zps_z1_write_basic_attributes(zigpy_device_from_v2_quirk):
    """Test writable basic attributes are converted to Tuya datapoints."""
    device = zigpy_device_from_v2_quirk("_TZE284_ft7qqpx3", "TS0601")
    cluster = device.endpoints[1].tuya_manufacturer

    with mock.patch.object(cluster, "_send_dp") as send_dp:
        result = await cluster.write_attributes(
            {
                "detection_range": 300,
                "presence_clear_cooldown": 30,
                "led_indicator": True,
                "energy_streaming": False,
                "sensitivity_preset": SensitivityPreset.low,
            }
        )

    assert result[0][0].status == foundation.Status.SUCCESS
    assert send_dp.call_count == 5


async def test_zps_z1_write_auto_calibration_starts_energy_stream(
    zigpy_device_from_v2_quirk,
):
    """Test auto calibration start enables energy streaming first."""
    device = zigpy_device_from_v2_quirk("_TZE284_ft7qqpx3", "TS0601")
    cluster = device.endpoints[1].tuya_manufacturer

    with (
        mock.patch.object(cluster, "_send_dp") as send_dp,
        mock.patch.object(cluster, "_start_keepalive"),
    ):
        result = await cluster.write_attributes(
            {"auto_calibration": AutoCalibrationCmd.start}
        )

    assert result[0][0].status == foundation.Status.SUCCESS
    assert send_dp.call_count == 2


async def test_zps_z1_write_zone_and_thresholds(zigpy_device_from_v2_quirk):
    """Test zone and threshold writes."""
    device = zigpy_device_from_v2_quirk("_TZE284_ft7qqpx3", "TS0601")
    cluster = device.endpoints[1].tuya_manufacturer

    cluster._thresholds_initialized = True

    with mock.patch.object(cluster, "_send_dp") as send_dp:
        result = await cluster.write_attributes(
            {
                "zone_7_active": False,
                "zone_1_motion_threshold": 20,
                "zone_1_presence_threshold": 10,
            }
        )

    assert result[0][0].status == foundation.Status.SUCCESS
    assert send_dp.call_count == 5


async def test_zps_z1_short_energy_payloads_are_ignored(zigpy_device_from_v2_quirk):
    """Test short raw payloads are accepted and ignored."""
    device = zigpy_device_from_v2_quirk("_TZE284_ft7qqpx3", "TS0601")
    cluster = device.endpoints[1].tuya_manufacturer

    for dp in (DP_ENERGY_VALUE, DP_ZONE_MAP, DP_ENERGY_THRESHOLD):
        hdr, data = cluster.deserialize(_dp_frame(dp, DT_RAW, b"\x01"))
        status = cluster.handle_get_data(data.data)

        assert status == foundation.Status.SUCCESS


async def test_zps_z1_load_thresholds_from_cache(zigpy_device_from_v2_quirk):
    """Test threshold state can be restored from cached attributes."""
    device = zigpy_device_from_v2_quirk("_TZE284_ft7qqpx3", "TS0601")
    cluster = device.endpoints[1].tuya_manufacturer

    attr_cache = {}
    for zone in range(1, 11):
        motion_attr = cluster.attributes_by_name[f"zone_{zone}_motion_threshold"].id
        presence_attr = cluster.attributes_by_name[f"zone_{zone}_presence_threshold"].id
        attr_cache[motion_attr] = 20
        attr_cache[presence_attr] = 10

    cluster._attr_cache = attr_cache
    cluster._thresholds_initialized = False

    assert cluster._load_thresholds_from_cache() is True
    assert cluster._thresholds_initialized is True
    assert cluster._motion_thr[0] == 51
    assert cluster._presence_thr[0] == 26


async def test_zps_z1_load_thresholds_from_cache_missing_attr(
    zigpy_device_from_v2_quirk,
):
    """Test threshold cache restore fails when cache is incomplete."""
    device = zigpy_device_from_v2_quirk("_TZE284_ft7qqpx3", "TS0601")
    cluster = device.endpoints[1].tuya_manufacturer

    cluster._attr_cache = {}

    assert cluster._load_thresholds_from_cache() is False


async def test_zps_z1_ensure_thresholds_initialized_failure(
    zigpy_device_from_v2_quirk,
):
    """Test threshold initialization failure when device/cache has no data."""
    device = zigpy_device_from_v2_quirk("_TZE284_ft7qqpx3", "TS0601")
    cluster = device.endpoints[1].tuya_manufacturer

    cluster._thresholds_initialized = False
    cluster._attr_cache = {}

    with (
        mock.patch.object(cluster, "_query_data"),
        mock.patch("zhaquirks.tuya.TS0601_TZE284_ft7qqpx3.asyncio.sleep"),
        pytest.raises(ValueError, match="energy thresholds are not initialized yet"),
    ):
        await cluster._ensure_thresholds_initialized()


async def test_zps_z1_disable_calibration_energy_stream(zigpy_device_from_v2_quirk):
    """Test calibration energy stream cleanup."""
    device = zigpy_device_from_v2_quirk("_TZE284_ft7qqpx3", "TS0601")
    cluster = device.endpoints[1].tuya_manufacturer

    cluster._energy_stream_on = True
    cluster._energy_stream_enabled_for_calibration = True
    cluster._update_attribute(cluster.attributes_by_name["energy_streaming"].id, True)

    with mock.patch.object(cluster, "_send_dp") as send_dp:
        await cluster._disable_calibration_energy_stream()

    send_dp.assert_awaited_once()
    assert cluster._energy_stream_on is False
    assert cluster._energy_stream_enabled_for_calibration is False

    success, _ = await cluster.read_attributes(("energy_streaming",))
    assert success["energy_streaming"] is False


async def test_zps_z1_write_attributes_failure_path(zigpy_device_from_v2_quirk):
    """Test write_attributes returns failure when a write raises."""
    device = zigpy_device_from_v2_quirk("_TZE284_ft7qqpx3", "TS0601")
    cluster = device.endpoints[1].tuya_manufacturer

    with mock.patch.object(cluster, "_set_attribute", side_effect=ValueError("boom")):
        result = await cluster.write_attributes({"detection_range": 300})

    assert result[0][0].status == foundation.Status.FAILURE
    assert result[0][0].attrid == cluster.attributes_by_name["detection_range"].id


async def test_zps_z1_first_message_initializes_calibration_status(
    zigpy_device_from_v2_quirk,
):
    """Test that the first received datapoint resets auto_calibration_status."""
    device = zigpy_device_from_v2_quirk("_TZE284_ft7qqpx3", "TS0601")
    cluster = device.endpoints[1].tuya_manufacturer

    assert cluster._first_message_received is False

    # Send a first datapoint; this triggers the _first_message_received branch.
    hdr, data = cluster.deserialize(_dp_frame(DP_PRESENCE_STATE, DT_ENUM, b"\x00"))
    cluster.handle_get_data(data.data)

    assert cluster._first_message_received is True

    success, _ = await cluster.read_attributes(("auto_calibration_status",))
    assert success["auto_calibration_status"] == "standby"

    # A second call must NOT re-initialise (branch not taken).
    hdr, data = cluster.deserialize(_dp_frame(DP_PRESENCE_STATE, DT_ENUM, b"\x01"))
    cluster.handle_get_data(data.data)
    # No assertion needed — just confirming no crash on second pass.


async def test_zps_z1_first_message_initializes_calibration_status(
    zigpy_device_from_v2_quirk,
):
    """Test that the first received datapoint resets auto_calibration_status."""
    device = zigpy_device_from_v2_quirk("_TZE284_ft7qqpx3", "TS0601")
    cluster = device.endpoints[1].tuya_manufacturer

    hdr, data = cluster.deserialize(_dp_frame(DP_PRESENCE_STATE, DT_ENUM, b"\x00"))
    cluster.handle_get_data(data.data)

    assert cluster._first_message_received is True

    success, _ = await cluster.read_attributes(("auto_calibration_status",))
    assert success["auto_calibration_status"] == "standby"

    # Second call — branch not taken, no crash.
    hdr, data = cluster.deserialize(_dp_frame(DP_PRESENCE_STATE, DT_ENUM, b"\x01"))
    cluster.handle_get_data(data.data)


async def test_zps_z1_first_message_flag_starts_false(zigpy_device_from_v2_quirk):
    """Test that _first_message_received starts as False before any message."""
    device = zigpy_device_from_v2_quirk("_TZE284_ft7qqpx3", "TS0601")
    cluster = device.endpoints[1].tuya_manufacturer

    assert cluster._first_message_received is False


async def test_zps_z1_zone_map_pending_write_match(zigpy_device_from_v2_quirk):
    """Test DP117 with _pending_zone_write=True and matching data clears the flag."""
    device = zigpy_device_from_v2_quirk("_TZE284_ft7qqpx3", "TS0601")
    cluster = device.endpoints[1].tuya_manufacturer

    # Force a known zone state and simulate a pending write whose echo matches.
    cluster._zone_active = [True] * 10
    cluster._pending_zone_write = True

    payload = bytes([1] * 10)
    hdr, data = cluster.deserialize(_dp_frame(DP_ZONE_MAP, DT_RAW, payload))
    cluster.handle_get_data(data.data)

    assert cluster._pending_zone_write is False

    success, _ = await cluster.read_attributes(("zone_1_active",))
    assert success["zone_1_active"] is True


async def test_zps_z1_zone_map_pending_write_mismatch(zigpy_device_from_v2_quirk):
    """Test DP117 mismatch while _pending_zone_write=True triggers a retry task."""
    device = zigpy_device_from_v2_quirk("_TZE284_ft7qqpx3", "TS0601")
    cluster = device.endpoints[1].tuya_manufacturer

    cluster._zone_active = [True] * 10
    cluster._pending_zone_write = True

    # Device echoes a different map → mismatch → _resend_zone_map is scheduled.
    mismatch_payload = bytes([0] * 10)
    with mock.patch.object(cluster, "create_catching_task") as mock_task:
        hdr, data = cluster.deserialize(
            _dp_frame(DP_ZONE_MAP, DT_RAW, mismatch_payload)
        )
        cluster.handle_get_data(data.data)

    mock_task.assert_called_once()
    # _pending_zone_write stays True (we returned early).
    assert cluster._pending_zone_write is True


async def test_zps_z1_write_auto_calibration_standby_is_noop(
    zigpy_device_from_v2_quirk,
):
    """Test writing auto_calibration=standby only updates the attribute, no DP sent."""
    device = zigpy_device_from_v2_quirk("_TZE284_ft7qqpx3", "TS0601")
    cluster = device.endpoints[1].tuya_manufacturer

    with mock.patch.object(cluster, "_send_dp") as send_dp:
        result = await cluster.write_attributes(
            {"auto_calibration": AutoCalibrationCmd.standby}
        )

    assert result[0][0].status == foundation.Status.SUCCESS
    send_dp.assert_not_called()

    success, _ = await cluster.read_attributes(("auto_calibration",))
    assert success["auto_calibration"] == AutoCalibrationCmd.standby


async def test_zps_z1_write_auto_calibration_cancel(zigpy_device_from_v2_quirk):
    """Test writing auto_calibration=cancel sends DP103 without enabling energy stream."""
    device = zigpy_device_from_v2_quirk("_TZE284_ft7qqpx3", "TS0601")
    cluster = device.endpoints[1].tuya_manufacturer

    with mock.patch.object(cluster, "_send_dp") as send_dp:
        result = await cluster.write_attributes(
            {"auto_calibration": AutoCalibrationCmd.cancel}
        )

    assert result[0][0].status == foundation.Status.SUCCESS
    # Only one DP sent: DP103 cancel — no energy-stream DP.
    assert send_dp.call_count == 1


async def test_zps_z1_write_auto_calibration_start_energy_stream_already_on(
    zigpy_device_from_v2_quirk,
):
    """Test auto_calibration=start skips energy-stream setup when already on."""
    device = zigpy_device_from_v2_quirk("_TZE284_ft7qqpx3", "TS0601")
    cluster = device.endpoints[1].tuya_manufacturer

    cluster._energy_stream_on = True

    with (
        mock.patch.object(cluster, "_send_dp") as send_dp,
        mock.patch.object(cluster, "_start_keepalive"),
    ):
        result = await cluster.write_attributes(
            {"auto_calibration": AutoCalibrationCmd.start}
        )

    assert result[0][0].status == foundation.Status.SUCCESS
    # Only DP103 is sent; no DP104 this time.
    assert send_dp.call_count == 1


async def test_zps_z1_sensitivity_preset_invalid_value(zigpy_device_from_v2_quirk):
    """Test DP112 ValueError fallback stores SensitivityPreset.custom."""
    device = zigpy_device_from_v2_quirk("_TZE284_ft7qqpx3", "TS0601")
    cluster = device.endpoints[1].tuya_manufacturer

    # Patch il costruttore di SensitivityPreset nel namespace del modulo
    # in modo che sollevi ValueError, simulando un valore non valido.
    original_cls = SensitivityPreset

    def raising_cls(val):
        raise ValueError("bad value")

    raising_cls.custom = original_cls.custom  # preserva .custom per il fallback

    with mock.patch(
        "zhaquirks.tuya.TS0601_TZE284_ft7qqpx3.SensitivityPreset",
        raising_cls,
    ):
        hdr, data = cluster.deserialize(
            _dp_frame(DP_SENSITIVITY_PRESET, DT_ENUM, b"\xff")
        )
        status = cluster.handle_get_data(data.data)

    assert status == foundation.Status.SUCCESS

    success, _ = await cluster.read_attributes(("sensitivity_preset",))
    assert success["sensitivity_preset"] == SensitivityPreset.custom


async def test_zps_z1_handle_cluster_specific_commands(zigpy_device_from_v2_quirk):
    """Test handle_cluster_specific_commands delegates to _process_tuya_datapoints."""
    device = zigpy_device_from_v2_quirk("_TZE284_ft7qqpx3", "TS0601")
    cluster = device.endpoints[1].tuya_manufacturer

    with mock.patch.object(
        cluster, "_process_tuya_datapoints", return_value=False
    ) as mock_proc:
        # Simulate args with dpValues attribute.
        args = mock.Mock()
        args.dpValues = []
        cluster.handle_cluster_specific_commands(tsn=1, command_id=0, args=args)

    mock_proc.assert_called_once_with([])


async def test_zps_z1_handle_cluster_specific_commands_no_dpvalues(
    zigpy_device_from_v2_quirk,
):
    """Test handle_cluster_specific_commands handles missing dpValues gracefully."""
    device = zigpy_device_from_v2_quirk("_TZE284_ft7qqpx3", "TS0601")
    cluster = device.endpoints[1].tuya_manufacturer

    with mock.patch.object(
        cluster, "_process_tuya_datapoints", return_value=False
    ) as mock_proc:
        args = mock.Mock(spec=[])  # no dpValues attribute
        cluster.handle_cluster_specific_commands(tsn=1, command_id=0, args=args)

    mock_proc.assert_called_once_with([])


async def test_zps_z1_disable_calibration_energy_stream_exception(
    zigpy_device_from_v2_quirk,
):
    """Test _disable_calibration_energy_stream catches and logs exceptions."""
    device = zigpy_device_from_v2_quirk("_TZE284_ft7qqpx3", "TS0601")
    cluster = device.endpoints[1].tuya_manufacturer

    cluster._energy_stream_on = True
    cluster._energy_stream_enabled_for_calibration = True

    with mock.patch.object(cluster, "_send_dp", side_effect=Exception("network error")):
        # Should not raise; exception is swallowed by the except block.
        await cluster._disable_calibration_energy_stream()


async def test_zps_z1_write_unhandled_attribute_key(zigpy_device_from_v2_quirk):
    """Test _set_attribute with an unknown key falls through to the debug-log else branch."""
    device = zigpy_device_from_v2_quirk("_TZE284_ft7qqpx3", "TS0601")
    cluster = device.endpoints[1].tuya_manufacturer

    # Directly call _set_attribute with a key that hits the final `else`.
    # We register a temporary fake attribute so write_attributes accepts it,
    # but the key has no matching branch in _set_attribute.
    with mock.patch.object(cluster, "_send_dp") as send_dp:
        await cluster._set_attribute("illuminance", 42)  # read-only, no branch

    send_dp.assert_not_called()


async def test_zps_z1_keepalive_loop_cancelled(zigpy_device_from_v2_quirk):
    """Test _keepalive_loop exits cleanly on CancelledError."""
    device = zigpy_device_from_v2_quirk("_TZE284_ft7qqpx3", "TS0601")
    cluster = device.endpoints[1].tuya_manufacturer

    with mock.patch(
        "zhaquirks.tuya.TS0601_TZE284_ft7qqpx3.asyncio.sleep",
        side_effect=CancelledError,
    ):
        await cluster._keepalive_loop()
    # Se arriviamo qui senza eccezioni, CancelledError è stato gestito correttamente.

    send_dp.assert_not_called()


async def test_zps_z1_auto_calibration_status_raw_values(zigpy_device_from_v2_quirk):
    """Test all CALIB_STATUS_MAP values via DP103."""
    device = zigpy_device_from_v2_quirk("_TZE284_ft7qqpx3", "TS0601")
    cluster = device.endpoints[1].tuya_manufacturer

    expected = {0: "standby", 1: "start", 4: "fail", 5: "cancel"}

    for raw, label in expected.items():
        hdr, data = cluster.deserialize(
            _dp_frame(DP_AI_SELF_LEARNING, DT_ENUM, bytes([raw]))
        )
        cluster.handle_get_data(data.data)

        success, _ = await cluster.read_attributes(("auto_calibration_status",))
        assert success["auto_calibration_status"] == label, f"raw={raw}"


async def test_zps_z1_enum_from_value_string_and_enum(zigpy_device_from_v2_quirk):
    """Test _enum_from_value with string name and already-enum input."""
    from zhaquirks.tuya.TS0601_TZE284_ft7qqpx3 import _enum_from_value

    # Already the right enum type.
    result = _enum_from_value(SensitivityPreset, SensitivityPreset.low)
    assert result is SensitivityPreset.low

    # String name lookup.
    result = _enum_from_value(SensitivityPreset, "medium")
    assert result == SensitivityPreset.medium

    # Invalid string → KeyError → returns None.
    result = _enum_from_value(SensitivityPreset, "nonexistent")
    assert result is None

    # Unknown int: t.enum8 does NOT raise ValueError, returns undefined_0xff.
    result = _enum_from_value(SensitivityPreset, 255)
    assert result is not None  # it's SensitivityPreset.undefined_0xff
