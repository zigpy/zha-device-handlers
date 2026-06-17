"""Tests for the Tuya TS0601 SPI/addressable LED quirk (Gledopto GL-SPI-206P)."""

from unittest import mock

from zigpy.quirks.v2 import CustomDeviceV2
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import LevelControl, OnOff
from zigpy.zcl.clusters.lighting import Color

from tests.common import ClusterListener, wait_for_zigpy_tasks
import zhaquirks
from zhaquirks.tuya import TuyaCommand, TuyaData, TuyaDatapointData
from zhaquirks.tuya.mcu import TuyaMCUCluster
from zhaquirks.tuya.ts0601_light import (
    TuyaColorControl,
    TuyaSpiLevelControl,
    TuyaSpiOnOff,
    TuyaWorkMode,
    decode_hue,
    decode_saturation,
    dp_to_level,
    dp_to_mireds,
    encode_color,
    level_to_dp,
    mireds_to_dp,
    xy_to_hs,
)

zhaquirks.setup()

MANUFACTURER = "_TZE284_gt5al3bl"
MODEL = "TS0601"


def test_encode_color_exact_bytes():
    """The DP 61 payload must match the Z2M byte layout exactly."""
    # pure red: hue 0, full saturation -> h=0, s=1000, v=1000
    assert encode_color(0, 254) == bytes.fromhex("0001011400000003e803e8")
    # max hue (254 -> 360 deg = 0x0168), full saturation
    assert encode_color(254, 254) == bytes.fromhex("0001011400016803e803e8")
    # zero saturation (h=0, s=0, v=1000)
    assert encode_color(0, 0) == bytes.fromhex("00010114000000000003e8")


def test_color_roundtrip():
    """Encoding then decoding hue/saturation returns the originals."""
    for hue, sat in ((0, 0), (127, 200), (254, 254), (60, 90)):
        raw = encode_color(hue, sat)
        assert decode_hue(raw) == hue
        assert decode_saturation(raw) == sat


def test_decode_short_payload_is_safe():
    """Malformed/short payloads decode to 0 rather than raising."""
    assert decode_hue(b"\x00\x01") == 0
    assert decode_saturation(b"") == 0


def test_level_scaling():
    """ZCL level 0-254 maps to Tuya brightness 10-1000."""
    assert level_to_dp(0) == 10
    assert level_to_dp(254) == 1000
    assert dp_to_level(1000) == 254
    assert dp_to_level(10) == 1


def test_color_temp_scaling():
    """Tuya color temp 0=warm/1000=cold maps to ZCL mireds (inverse)."""
    assert mireds_to_dp(500) == 0
    assert mireds_to_dp(153) == 1000
    assert dp_to_mireds(0) == 500
    assert dp_to_mireds(1000) == 153


async def test_gl_spi_206p_clusters(zigpy_device_from_v2_quirk):
    """The quirk builds a color light with the expected clusters."""
    quirked = zigpy_device_from_v2_quirk(MANUFACTURER, MODEL)
    assert isinstance(quirked, CustomDeviceV2)

    ep = quirked.endpoints[1]
    assert isinstance(ep.on_off, OnOff)
    assert isinstance(ep.level, LevelControl)
    assert isinstance(ep.light_color, TuyaColorControl)
    assert isinstance(ep.tuya_manufacturer, TuyaMCUCluster)

    # zha only supports XY + color temp, so advertise those capabilities
    caps = ep.light_color.get(Color.AttributeDefs.color_capabilities.name)
    assert caps == (
        Color.ColorCapabilities.XY_attributes
        | Color.ColorCapabilities.Color_temperature
    )


def test_xy_to_hs_known_colors():
    """CIE xy converts to sensible ZCL hue (0-254) for primary colors."""
    red_hue, _ = xy_to_hs(int(0.69 * 65535), int(0.31 * 65535))
    assert red_hue <= 5 or red_hue >= 250  # hue wraps around 0
    green_hue, _ = xy_to_hs(int(0.17 * 65535), int(0.70 * 65535))
    assert 78 <= green_hue <= 95  # ~120 deg
    blue_hue, _ = xy_to_hs(int(0.15 * 65535), int(0.06 * 65535))
    assert 160 <= blue_hue <= 185  # ~240-250 deg


async def test_move_to_color_sends_dp61(zigpy_device_from_v2_quirk):
    """An XY color command (as zha sends it) sets colour mode + DP 61."""
    quirked = zigpy_device_from_v2_quirk(MANUFACTURER, MODEL)
    ep = quirked.endpoints[1]
    color = ep.light_color
    tuya = ep.tuya_manufacturer

    color_x, color_y = int(0.7 * 65535), int(0.3 * 65535)
    exp_hue, exp_sat = xy_to_hs(color_x, color_y)

    with mock.patch.object(
        tuya.endpoint, "request", return_value=foundation.Status.SUCCESS
    ) as req_mock:
        # zha invokes the named command with keyword args
        await color.command(
            Color.ServerCommandDefs.move_to_color.id,
            color_x=color_x,
            color_y=color_y,
            transition_time=0,
        )
        await wait_for_zigpy_tasks()

    sent = b"".join(
        (call.kwargs.get("data") or b"") for call in req_mock.call_args_list
    )

    # DP 2 (work_mode) set to colour: dp=0x02, enum type=0x04, len=1, value=1
    assert b"\x02\x04\x00\x01\x01" in sent
    # DP 61 raw payload: dp=0x3d, raw type=0x00, len=0x0b, then 11 HSV bytes
    assert b"\x3d\x00\x00\x0b" + encode_color(exp_hue, exp_sat) in sent

    # optimistic state: zha reads current_x/current_y
    assert color.get(Color.AttributeDefs.current_x.name) == color_x
    assert color.get(Color.AttributeDefs.current_y.name) == color_y
    assert color.get(Color.AttributeDefs.color_mode.name) == Color.ColorMode.X_and_Y

    # datapoints are sent fire-and-forget so streamed updates stay responsive
    assert req_mock.call_args_list
    assert all(
        call.kwargs.get("expect_reply") is False for call in req_mock.call_args_list
    )


async def test_work_mode_not_resent_when_unchanged(zigpy_device_from_v2_quirk):
    """work_mode (DP 2) is only sent when the mode changes, not every update.

    Resending it on every streamed colour update floods the MCU and causes the
    dropped/laggy commands users see when dragging the colour wheel.
    """
    quirked = zigpy_device_from_v2_quirk(MANUFACTURER, MODEL)
    ep = quirked.endpoints[1]
    color = ep.light_color
    tuya = ep.tuya_manufacturer

    work_mode_colour = b"\x02\x04\x00\x01\x01"  # DP 2 enum -> colour

    # first colour command: mode changes (None -> colour), so DP 2 is sent
    with mock.patch.object(
        tuya.endpoint, "request", return_value=foundation.Status.SUCCESS
    ) as req1:
        await color.command(
            Color.ServerCommandDefs.move_to_color.id,
            color_x=30000,
            color_y=30000,
            transition_time=0,
        )
        await wait_for_zigpy_tasks()
    sent1 = b"".join((c.kwargs.get("data") or b"") for c in req1.call_args_list)
    assert work_mode_colour in sent1

    # second colour command: already in colour mode, so DP 2 is NOT resent
    with mock.patch.object(
        tuya.endpoint, "request", return_value=foundation.Status.SUCCESS
    ) as req2:
        await color.command(
            Color.ServerCommandDefs.move_to_color.id,
            color_x=40000,
            color_y=20000,
            transition_time=0,
        )
        await wait_for_zigpy_tasks()
    sent2 = b"".join((c.kwargs.get("data") or b"") for c in req2.call_args_list)
    assert work_mode_colour not in sent2
    # the colour itself (DP 61) is still sent every time
    assert b"\x3d\x00\x00\x0b" in sent2


async def test_move_to_color_temp_sends_dp4(zigpy_device_from_v2_quirk):
    """A color-temp command sets white mode (DP 2) and color temp (DP 4)."""
    quirked = zigpy_device_from_v2_quirk(MANUFACTURER, MODEL)
    ep = quirked.endpoints[1]
    color = ep.light_color
    tuya = ep.tuya_manufacturer

    with mock.patch.object(
        tuya.endpoint, "request", return_value=foundation.Status.SUCCESS
    ) as req_mock:
        # zha invokes move_to_color_temp with keyword args
        await color.command(
            Color.ServerCommandDefs.move_to_color_temp.id,
            color_temp_mireds=326,
            transition_time=0,
        )
        await wait_for_zigpy_tasks()

    sent = b"".join(
        (call.kwargs.get("data") or b"") for call in req_mock.call_args_list
    )

    # DP 2 (work_mode) set to white (value 0)
    assert b"\x02\x04\x00\x01\x00" in sent
    # DP 4 (color_temp) value type, 4-byte big-endian value
    expected_dp4 = mireds_to_dp(326)
    assert b"\x04\x02\x00\x04" + expected_dp4.to_bytes(4, "big") in sent

    assert color.get(Color.AttributeDefs.color_temperature.name) == 326
    assert (
        color.get(Color.AttributeDefs.color_mode.name)
        == Color.ColorMode.Color_temperature
    )


async def test_brightness_command_sends_dp3(zigpy_device_from_v2_quirk):
    """A level command writes the scaled brightness on DP 3."""
    quirked = zigpy_device_from_v2_quirk(MANUFACTURER, MODEL)
    ep = quirked.endpoints[1]
    level = ep.level
    tuya = ep.tuya_manufacturer

    with mock.patch.object(
        tuya.endpoint, "request", return_value=foundation.Status.SUCCESS
    ) as req_mock:
        await level.command(
            LevelControl.ServerCommandDefs.move_to_level_with_on_off.id, 127, 0
        )
        await wait_for_zigpy_tasks()

    sent = b"".join(
        (call.kwargs.get("data") or b"") for call in req_mock.call_args_list
    )

    # DP 3 value type, 4-byte big-endian scaled brightness
    expected_dp3 = level_to_dp(127)
    assert b"\x03\x02\x00\x04" + expected_dp3.to_bytes(4, "big") in sent

    # brightness also goes out fire-and-forget for streaming responsiveness
    assert isinstance(level, TuyaSpiLevelControl)
    assert all(
        call.kwargs.get("expect_reply") is False for call in req_mock.call_args_list
    )


async def test_onoff_command_fire_and_forget(zigpy_device_from_v2_quirk):
    """on/off is sent expect_reply=False so a slow device can't stall the queue."""
    quirked = zigpy_device_from_v2_quirk(MANUFACTURER, MODEL)
    ep = quirked.endpoints[1]
    onoff = ep.on_off
    tuya = ep.tuya_manufacturer

    assert isinstance(onoff, TuyaSpiOnOff)

    with mock.patch.object(
        tuya.endpoint, "request", return_value=foundation.Status.SUCCESS
    ) as req_mock:
        await onoff.command(OnOff.ServerCommandDefs.on.id)
        await wait_for_zigpy_tasks()

    sent = b"".join((c.kwargs.get("data") or b"") for c in req_mock.call_args_list)
    assert b"\x01\x01\x00\x01\x01" in sent  # DP 1 bool -> on
    assert req_mock.call_args_list
    assert all(c.kwargs.get("expect_reply") is False for c in req_mock.call_args_list)


async def test_incoming_color_report_updates_hue_sat(zigpy_device_from_v2_quirk):
    """An incoming DP 61 report updates both hue and saturation."""
    quirked = zigpy_device_from_v2_quirk(MANUFACTURER, MODEL)
    ep = quirked.endpoints[1]
    color = ep.light_color
    tuya = ep.tuya_manufacturer

    listener = ClusterListener(color)

    tuya.handle_get_data(
        TuyaCommand(
            status=0,
            tsn=1,
            # encode_color returns a t.Bytes, which TuyaData treats as a RAW DP
            datapoints=[TuyaDatapointData(61, TuyaData(encode_color(127, 200)))],
        )
    )

    assert color.get(Color.AttributeDefs.current_hue.name) == 127
    assert color.get(Color.AttributeDefs.current_saturation.name) == 200
    assert len(listener.attribute_updates) == 2


async def test_work_mode_select(zigpy_device_from_v2_quirk):
    """The work_mode enum is exposed on the manufacturer cluster."""
    quirked = zigpy_device_from_v2_quirk(MANUFACTURER, MODEL)
    ep = quirked.endpoints[1]
    tuya = ep.tuya_manufacturer

    tuya.handle_get_data(
        TuyaCommand(
            status=0,
            tsn=1,
            datapoints=[TuyaDatapointData(2, TuyaData(TuyaWorkMode.music))],
        )
    )
    assert tuya.get("work_mode") == TuyaWorkMode.music
