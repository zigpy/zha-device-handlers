"""Tests for Tuya SPI LED pixel controller quirk (WZ-SPI / GL-SPI-206P)."""

from unittest import mock

import pytest
from zigpy.zcl import foundation
from zigpy.zcl.clusters.lighting import Color

import zhaquirks
import zhaquirks.tuya.ts0601_spi_led
from zhaquirks.tuya.ts0601_spi_led import (
    SpiLedManufCluster,
    WorkMode,
    _dp61_payload,
    _dp61_to_hue,
    _dp61_to_sat,
    _enhanced_hue_to_hue_254,
    _level_from_device,
    _level_to_device,
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
