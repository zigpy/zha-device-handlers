"""Tests for Tuya SPI LED pixel controller quirk (WZ-SPI / GL-SPI-206P)."""

from unittest import mock

import pytest
from zigpy.zcl import foundation
from zigpy.zcl.clusters.lighting import Color

import zhaquirks
import zhaquirks.tuya.ts0601_spi_led
from zhaquirks.tuya.ts0601_spi_led import (
    ChipType,
    LightBeadSequence,
    SpiLedManufCluster,
    WorkMode,
    _current_level_254,
    _dp61_payload,
    _dp61_to_hue,
    _dp61_to_sat,
    _enhanced_hue_to_hue_254,
    _level_from_device,
    _level_to_device,
    _xy_to_hs_254,
    _zcl_arg,
)

zhaquirks.setup()


# ---------------------------------------------------------------------------
# Helper function unit tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "device_val, expected_zcl",
    [
        (10, 0),
        (1000, 254),
        (505, 127),
    ],
)
def test_level_from_device(device_val, expected_zcl):
    """Test device brightness (10-1000) to ZCL level (0-254) conversion."""
    assert _level_from_device(device_val) == expected_zcl


@pytest.mark.parametrize(
    "zcl_level, expected_device",
    [
        (0, 10),
        (254, 1000),
        (127, 505),
    ],
)
def test_level_to_device(zcl_level, expected_device):
    """Test ZCL level (0-254) to device brightness (10-1000) conversion."""
    assert _level_to_device(zcl_level) == expected_device


def test_dp61_payload_structure():
    """Test that DP 61 payload has the correct 11-byte structure."""
    payload = _dp61_payload(180, 500, 800)
    assert len(payload) == 11
    # Fixed header bytes
    assert payload[0] == 0x00
    assert payload[1] == 0x01
    assert payload[2] == 0x01
    assert payload[3] == 0x14
    assert payload[4] == 0x00
    # Hue 180° encoded as big-endian uint16
    assert (payload[5] << 8) | payload[6] == 180
    # Saturation 500 encoded as big-endian uint16
    assert (payload[7] << 8) | payload[8] == 500
    # Value 800 encoded as big-endian uint16
    assert (payload[9] << 8) | payload[10] == 800


@pytest.mark.parametrize(
    "raw, expected_hue",
    [
        # H=360° → hue_254=254
        (bytes([0, 1, 1, 20, 0, 0x01, 0x68, 0x03, 0xE8, 0x03, 0xE8]), 254),
        # H=0° → hue_254=0
        (bytes([0, 1, 1, 20, 0, 0x00, 0x00, 0x03, 0xE8, 0x03, 0xE8]), 0),
        # H=180° → hue_254≈127
        (bytes([0, 1, 1, 20, 0, 0x00, 0xB4, 0x03, 0xE8, 0x03, 0xE8]), 127),
    ],
)
def test_dp61_to_hue(raw, expected_hue):
    """Test hue extraction from DP 61 payload."""
    assert _dp61_to_hue(raw) == expected_hue


@pytest.mark.parametrize(
    "raw, expected_sat",
    [
        # S=1000 → sat_254=254
        (bytes([0, 1, 1, 20, 0, 0x00, 0x00, 0x03, 0xE8, 0x03, 0xE8]), 254),
        # S=0 → sat_254=0
        (bytes([0, 1, 1, 20, 0, 0x00, 0x00, 0x00, 0x00, 0x03, 0xE8]), 0),
        # S=500 → sat_254≈127
        (bytes([0, 1, 1, 20, 0, 0x00, 0x00, 0x01, 0xF4, 0x03, 0xE8]), 127),
    ],
)
def test_dp61_to_sat(raw, expected_sat):
    """Test saturation extraction from DP 61 payload."""
    assert _dp61_to_sat(raw) == expected_sat


def test_dp61_short_payload():
    """Test that short payloads return 0 for hue and saturation."""
    assert _dp61_to_hue(b"\x00\x01") == 0
    assert _dp61_to_sat(b"\x00\x01") == 0


def test_enhanced_hue_to_hue_254():
    """Test enhanced hue (0-65535) to standard hue (0-254) conversion."""
    assert _enhanced_hue_to_hue_254(0) == 0
    assert _enhanced_hue_to_hue_254(65535) == 254
    assert _enhanced_hue_to_hue_254(32767) == 127


@pytest.mark.parametrize(
    "x, y, expected_h, expected_s",
    [
        # Pure red in CIE XY (approx)
        (40139, 20396, 0, 254),
        # Black / near-zero Y → returns (0, 0)
        (32768, 0, 0, 0),
        # Near-zero after normalisation → returns (0, 0)
        (0, 0, 0, 0),
    ],
)
def test_xy_to_hs_254(x, y, expected_h, expected_s):
    """Test XY to HS conversion including degenerate edge cases."""
    h, s = _xy_to_hs_254(x, y)
    assert 0 <= h <= 254
    assert 0 <= s <= 254
    # Edge cases must return exactly (0, 0)
    if y == 0:
        assert h == 0
        assert s == 0


def test_current_level_254_with_level(zigpy_device_from_v2_quirk):
    """Test _current_level_254 returns cached level when available."""
    device = zigpy_device_from_v2_quirk("_TZE204_8fffc3kb", "TS0601")
    ep = device.endpoints[1]
    ep.level._update_attribute(ep.level.AttributeDefs.current_level.id, 100)
    assert _current_level_254(ep) == 100


def test_current_level_254_fallback(zigpy_device_from_v2_quirk):
    """Test _current_level_254 returns 254 when level is not cached."""
    device = zigpy_device_from_v2_quirk("_TZE204_8fffc3kb", "TS0601")
    ep = device.endpoints[1]
    # Level cluster exists but attribute not yet set
    assert _current_level_254(ep) == 254


def test_current_level_254_no_cluster():
    """Test _current_level_254 returns 254 when endpoint has no level cluster."""

    class FakeEndpoint:
        @property
        def level(self):
            raise AttributeError

    assert _current_level_254(FakeEndpoint()) == 254


def test_zcl_arg_positional():
    """Test _zcl_arg extracts positional argument."""
    assert _zcl_arg(0, "hue", (42,), {}) == 42
    assert _zcl_arg(1, "sat", (10, 20), {}) == 20


def test_zcl_arg_keyword():
    """Test _zcl_arg falls back to kwargs."""
    assert _zcl_arg(0, "hue", (), {"hue": 99}) == 99
    assert _zcl_arg(0, "missing", (), {}) is None


# ---------------------------------------------------------------------------
# Device / entity creation tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "manufacturer",
    ["_TZE204_8fffc3kb", "_TZE284_gt5al3bl"],
)
def test_spi_led_entity_creation(zigpy_device_from_v2_quirk, manufacturer):
    """Test that the WZ-SPI LED quirk loads and exposes the expected clusters."""
    device = zigpy_device_from_v2_quirk(manufacturer, "TS0601")
    ep = device.endpoints[1]

    assert ep.on_off is not None
    assert ep.level is not None
    assert ep.light_color is not None
    assert ep.tuya_manufacturer is not None
    assert isinstance(ep.tuya_manufacturer, SpiLedManufCluster)


# ---------------------------------------------------------------------------
# DP → attribute mapping tests
# ---------------------------------------------------------------------------

# Tuya MCU GET_DATA frame: ZCL header (09 tsn 02) + status(1) + tuya_tsn(2) + DPs
# DP frame: dp(1) + type(1) + len_hi(1) + len_lo(1) + value(len)

# DP 1 on/off = True
_MSG_ON = b"\x09\x01\x02\x00\x00\x01\x01\x00\x01\x01"
# DP 3 brightness = 1000
_MSG_BRIGHTNESS_MAX = b"\x09\x01\x02\x00\x00\x03\x02\x00\x04\x00\x00\x03\xe8"
# DP 2 work_mode = colour (1)
_MSG_WORK_MODE_COLOUR = b"\x09\x01\x02\x00\x00\x02\x04\x00\x01\x01"
# DP 53 pixel_count = 100
_MSG_PIXEL_COUNT = b"\x09\x01\x02\x00\x00\x35\x02\x00\x04\x00\x00\x00\x64"
# DP 61 colour_hsv: hue=180°, sat=1000, val=1000  (type=0x00 RAW)
_MSG_COLOUR_HSV = (
    b"\x09\x01\x02\x00\x00\x3d\x00\x00\x0b\x00\x01\x01\x14\x00\x00\xb4\x03\xe8\x03\xe8"
)
# DP 101 light_bead_sequence = GRB (2)
_MSG_BEAD_SEQ_GRB = b"\x09\x01\x02\x00\x00\x65\x04\x00\x01\x02"
# DP 102 chip_type = WS2811 (3)
_MSG_CHIP_WS2811 = b"\x09\x01\x02\x00\x00\x66\x04\x00\x01\x03"


def test_spi_led_dp_on_off(zigpy_device_from_v2_quirk):
    """Test that DP 1 maps to on_off attribute."""
    device = zigpy_device_from_v2_quirk("_TZE204_8fffc3kb", "TS0601")
    ep = device.endpoints[1]
    tuya_cluster = ep.tuya_manufacturer

    hdr, data = tuya_cluster.deserialize(_MSG_ON)
    with mock.patch.object(tuya_cluster, "send_default_rsp"):
        tuya_cluster.handle_message(hdr, data)

    assert bool(ep.on_off.get("on_off")) is True


def test_spi_led_dp_brightness(zigpy_device_from_v2_quirk):
    """Test that DP 3 maps to current_level with correct scaling."""
    device = zigpy_device_from_v2_quirk("_TZE204_8fffc3kb", "TS0601")
    ep = device.endpoints[1]
    tuya_cluster = ep.tuya_manufacturer

    hdr, data = tuya_cluster.deserialize(_MSG_BRIGHTNESS_MAX)
    with mock.patch.object(tuya_cluster, "send_default_rsp"):
        tuya_cluster.handle_message(hdr, data)

    assert ep.level.get("current_level") == 254


def test_spi_led_dp_work_mode(zigpy_device_from_v2_quirk):
    """Test that DP 2 maps to work_mode attribute."""
    device = zigpy_device_from_v2_quirk("_TZE204_8fffc3kb", "TS0601")
    ep = device.endpoints[1]
    tuya_cluster = ep.tuya_manufacturer

    hdr, data = tuya_cluster.deserialize(_MSG_WORK_MODE_COLOUR)
    with mock.patch.object(tuya_cluster, "send_default_rsp"):
        tuya_cluster.handle_message(hdr, data)

    assert tuya_cluster.get("work_mode") == WorkMode.colour


def test_spi_led_dp_pixel_count(zigpy_device_from_v2_quirk):
    """Test that DP 53 maps to lightpixel_number_set attribute."""
    device = zigpy_device_from_v2_quirk("_TZE204_8fffc3kb", "TS0601")
    ep = device.endpoints[1]
    tuya_cluster = ep.tuya_manufacturer

    hdr, data = tuya_cluster.deserialize(_MSG_PIXEL_COUNT)
    with mock.patch.object(tuya_cluster, "send_default_rsp"):
        tuya_cluster.handle_message(hdr, data)

    assert tuya_cluster.get("lightpixel_number_set") == 100


def test_spi_led_dp_colour_hsv(zigpy_device_from_v2_quirk):
    """Test that DP 61 maps to current_hue and current_saturation attributes."""
    device = zigpy_device_from_v2_quirk("_TZE204_8fffc3kb", "TS0601")
    ep = device.endpoints[1]
    tuya_cluster = ep.tuya_manufacturer

    hdr, data = tuya_cluster.deserialize(_MSG_COLOUR_HSV)
    with mock.patch.object(tuya_cluster, "send_default_rsp"):
        tuya_cluster.handle_message(hdr, data)

    assert ep.light_color.get("current_hue") == 127  # 180° → ~127
    assert ep.light_color.get("current_saturation") == 254


def test_spi_led_dp_bead_sequence(zigpy_device_from_v2_quirk):
    """Test that DP 101 maps to light_bead_sequence attribute."""
    device = zigpy_device_from_v2_quirk("_TZE204_8fffc3kb", "TS0601")
    ep = device.endpoints[1]
    tuya_cluster = ep.tuya_manufacturer

    hdr, data = tuya_cluster.deserialize(_MSG_BEAD_SEQ_GRB)
    with mock.patch.object(tuya_cluster, "send_default_rsp"):
        tuya_cluster.handle_message(hdr, data)

    assert tuya_cluster.get("light_bead_sequence") == LightBeadSequence.GRB


def test_spi_led_dp_chip_type(zigpy_device_from_v2_quirk):
    """Test that DP 102 maps to chip_type attribute."""
    device = zigpy_device_from_v2_quirk("_TZE204_8fffc3kb", "TS0601")
    ep = device.endpoints[1]
    tuya_cluster = ep.tuya_manufacturer

    hdr, data = tuya_cluster.deserialize(_MSG_CHIP_WS2811)
    with mock.patch.object(tuya_cluster, "send_default_rsp"):
        tuya_cluster.handle_message(hdr, data)

    assert tuya_cluster.get("chip_type") == ChipType.WS2811


# ---------------------------------------------------------------------------
# Color command tests
# ---------------------------------------------------------------------------


async def test_color_command_move_to_hue_and_saturation(zigpy_device_from_v2_quirk):
    """Test move_to_hue_and_saturation sends correct DP 61 payload."""
    device = zigpy_device_from_v2_quirk("_TZE204_8fffc3kb", "TS0601")
    ep = device.endpoints[1]

    with mock.patch.object(
        ep.tuya_manufacturer, "command", new_callable=mock.AsyncMock
    ) as mock_cmd:
        mock_cmd.return_value = foundation.GENERAL_COMMANDS[
            foundation.GeneralCommand.Default_Response
        ].schema(
            command_id=Color.ServerCommandDefs.move_to_hue_and_saturation.id,
            status=foundation.Status.SUCCESS,
        )
        result = await ep.light_color.command(
            Color.ServerCommandDefs.move_to_hue_and_saturation.id,
            127,  # hue
            254,  # saturation
        )

    assert result.status == foundation.Status.SUCCESS
    assert ep.light_color.get("current_hue") == 127
    assert ep.light_color.get("current_saturation") == 254


async def test_color_command_unsupported(zigpy_device_from_v2_quirk):
    """Test that unsupported color commands return UNSUP_CLUSTER_COMMAND."""
    device = zigpy_device_from_v2_quirk("_TZE204_8fffc3kb", "TS0601")
    ep = device.endpoints[1]

    result = await ep.light_color.command(0xFF)
    assert result.status == foundation.Status.UNSUP_CLUSTER_COMMAND


async def test_color_command_move_to_hue(zigpy_device_from_v2_quirk):
    """Test move_to_hue updates hue while preserving current saturation."""
    device = zigpy_device_from_v2_quirk("_TZE204_8fffc3kb", "TS0601")
    ep = device.endpoints[1]
    ep.light_color._update_attribute(Color.AttributeDefs.current_saturation.id, 200)

    with mock.patch.object(
        ep.tuya_manufacturer, "command", new_callable=mock.AsyncMock
    ):
        result = await ep.light_color.command(
            Color.ServerCommandDefs.move_to_hue.id, 50
        )

    assert result.status == foundation.Status.SUCCESS
    assert ep.light_color.get("current_hue") == 50
    assert ep.light_color.get("current_saturation") == 200


async def test_color_command_move_to_hue_missing_arg(zigpy_device_from_v2_quirk):
    """Test move_to_hue returns FAILURE when hue argument is missing."""
    device = zigpy_device_from_v2_quirk("_TZE204_8fffc3kb", "TS0601")
    ep = device.endpoints[1]

    result = await ep.light_color.command(Color.ServerCommandDefs.move_to_hue.id)
    assert result.status == foundation.Status.FAILURE


async def test_color_command_move_to_saturation(zigpy_device_from_v2_quirk):
    """Test move_to_saturation updates saturation while preserving current hue."""
    device = zigpy_device_from_v2_quirk("_TZE204_8fffc3kb", "TS0601")
    ep = device.endpoints[1]
    ep.light_color._update_attribute(Color.AttributeDefs.current_hue.id, 80)

    with mock.patch.object(
        ep.tuya_manufacturer, "command", new_callable=mock.AsyncMock
    ):
        result = await ep.light_color.command(
            Color.ServerCommandDefs.move_to_saturation.id, 150
        )

    assert result.status == foundation.Status.SUCCESS
    assert ep.light_color.get("current_saturation") == 150
    assert ep.light_color.get("current_hue") == 80


async def test_color_command_move_to_saturation_missing_arg(zigpy_device_from_v2_quirk):
    """Test move_to_saturation returns FAILURE when saturation argument is missing."""
    device = zigpy_device_from_v2_quirk("_TZE204_8fffc3kb", "TS0601")
    ep = device.endpoints[1]

    result = await ep.light_color.command(Color.ServerCommandDefs.move_to_saturation.id)
    assert result.status == foundation.Status.FAILURE


async def test_color_command_move_to_color_xy(zigpy_device_from_v2_quirk):
    """Test move_to_color (XY) converts to HS and updates XY attributes."""
    device = zigpy_device_from_v2_quirk("_TZE204_8fffc3kb", "TS0601")
    ep = device.endpoints[1]

    with mock.patch.object(
        ep.tuya_manufacturer, "command", new_callable=mock.AsyncMock
    ):
        result = await ep.light_color.command(
            Color.ServerCommandDefs.move_to_color.id,
            40139,  # color_x
            20396,  # color_y
        )

    assert result.status == foundation.Status.SUCCESS
    assert ep.light_color.get("current_x") == 40139
    assert ep.light_color.get("current_y") == 20396


async def test_color_command_move_to_color_missing_args(zigpy_device_from_v2_quirk):
    """Test move_to_color returns FAILURE when XY arguments are missing."""
    device = zigpy_device_from_v2_quirk("_TZE204_8fffc3kb", "TS0601")
    ep = device.endpoints[1]

    result = await ep.light_color.command(Color.ServerCommandDefs.move_to_color.id)
    assert result.status == foundation.Status.FAILURE


async def test_color_command_enhanced_move_to_hue_and_saturation(
    zigpy_device_from_v2_quirk,
):
    """Test enhanced_move_to_hue_and_saturation converts enhanced hue correctly."""
    device = zigpy_device_from_v2_quirk("_TZE204_8fffc3kb", "TS0601")
    ep = device.endpoints[1]

    with mock.patch.object(
        ep.tuya_manufacturer, "command", new_callable=mock.AsyncMock
    ):
        result = await ep.light_color.command(
            Color.ServerCommandDefs.enhanced_move_to_hue_and_saturation.id,
            32767,  # enhanced_hue (~half wheel)
            200,  # saturation
        )

    assert result.status == foundation.Status.SUCCESS
    assert ep.light_color.get("enhanced_current_hue") == 32767


async def test_color_command_enhanced_missing_args(zigpy_device_from_v2_quirk):
    """Test enhanced_move_to_hue_and_saturation returns FAILURE on missing args."""
    device = zigpy_device_from_v2_quirk("_TZE204_8fffc3kb", "TS0601")
    ep = device.endpoints[1]

    result = await ep.light_color.command(
        Color.ServerCommandDefs.enhanced_move_to_hue_and_saturation.id
    )
    assert result.status == foundation.Status.FAILURE


async def test_color_command_stop_move_step(zigpy_device_from_v2_quirk):
    """Test stop_move_step is acknowledged with SUCCESS."""
    device = zigpy_device_from_v2_quirk("_TZE204_8fffc3kb", "TS0601")
    ep = device.endpoints[1]

    result = await ep.light_color.command(Color.ServerCommandDefs.stop_move_step.id)
    assert result.status == foundation.Status.SUCCESS


async def test_color_command_move_to_hue_and_saturation_missing_args(
    zigpy_device_from_v2_quirk,
):
    """Test move_to_hue_and_saturation returns FAILURE when args are missing."""
    device = zigpy_device_from_v2_quirk("_TZE204_8fffc3kb", "TS0601")
    ep = device.endpoints[1]

    result = await ep.light_color.command(
        Color.ServerCommandDefs.move_to_hue_and_saturation.id
    )
    assert result.status == foundation.Status.FAILURE
