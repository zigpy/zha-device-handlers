"""Tuya SPI LED pixel controller (WZ-SPI / GL-SPI-206P).

Supported devices:
- _TZE204_8fffc3kb TS0601 (Gledopto / WZ-SPI GL-SPI-206P)
- _TZE284_gt5al3bl TS0601

DP MAP
------
DP  1  on/off            bool
DP  2  work_mode         enum  0=white 1=colour 2=scene 3=music
DP  3  brightness        value 10-1000
DP 53  pixel_count       value 10-1000
DP 61  colour_hsv        raw   (11-byte HSV payload)
DP101  light_bead_seq    enum
DP102  chip_type         enum
"""

from __future__ import annotations

import colorsys
from typing import Any, Final

from zigpy.profiles import zha
from zigpy.quirks.v2 import CustomDeviceV2, QuirkBuilder
from zigpy.quirks.v2.homeassistant import EntityType
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.lighting import Color
from zigpy.zcl.foundation import ZCLAttributeDef

from zhaquirks.tuya import (
    TUYA_CLUSTER_ID,
    TUYA_SET_DATA,
    BaseEnchantedDevice,
    Data,
    TuyaCommand,
    TuyaData,
    TuyaDatapointData,
    TuyaLocalCluster,
)
from zhaquirks.tuya.mcu import (
    DPToAttributeMapping,
    TuyaLevelControl,
    TuyaMCUCluster,
    TuyaOnOffNM,
)

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class WorkMode(t.enum8):
    """Work mode for the LED controller."""

    white = 0x00
    colour = 0x01
    scene = 0x02
    music = 0x03


class LightBeadSequence(t.enum8):
    """LED bead colour order — DP 101."""

    RGB = 0x00
    RBG = 0x01
    GRB = 0x02
    GBR = 0x03
    BRG = 0x04
    BGR = 0x05
    RGBW = 0x06
    RBGW = 0x07
    GRBW = 0x08
    GBRW = 0x09
    BRGW = 0x0A
    BGRW = 0x0B
    WRGB = 0x0C
    WRBG = 0x0D
    WGRB = 0x0E
    WGBR = 0x0F
    WBRG = 0x10
    WBGR = 0x11


class ChipType(t.enum8):
    """SPI LED chip model — DP 102."""

    WS2801 = 0x00
    LPD6803 = 0x01
    LPD8803 = 0x02
    WS2811 = 0x03
    TM1814B = 0x04
    TM1934A = 0x05
    SK6812 = 0x06
    SK9822 = 0x07
    UCS8904B = 0x08
    WS2805 = 0x09


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def _dp61_payload(h_deg: int, sat_1000: int, val_1000: int = 1000) -> Data:
    """Build 11-byte DP 61 colour payload."""
    h = max(0, min(360, int(h_deg)))
    s = max(0, min(1000, int(sat_1000)))
    v = max(0, min(1000, int(val_1000)))
    return Data(
        [
            0x00,
            0x01,
            0x01,
            0x14,
            0x00,
            (h >> 8) & 0xFF,
            h & 0xFF,
            (s >> 8) & 0xFF,
            s & 0xFF,
            (v >> 8) & 0xFF,
            v & 0xFF,
        ]
    )


def _dp61_to_hue(raw: bytes) -> int:
    """Extract hue from DP 61 payload (0-254 range)."""
    if len(raw) < 9:
        return 0
    h = (raw[5] << 8) | raw[6]
    return max(0, min(254, round(h * 254 / 360)))


def _dp61_to_sat(raw: bytes) -> int:
    """Extract saturation from DP 61 payload (0-254 range)."""
    if len(raw) < 9:
        return 0
    s = (raw[7] << 8) | raw[8]
    return max(0, min(254, round(s * 254 / 1000)))


def _level_from_device(raw: int) -> int:
    """Convert device brightness (10-1000) to ZCL level (0-254)."""
    raw = max(10, min(1000, int(raw)))
    return max(0, min(254, round((raw - 10) * 254 / 990)))


def _level_to_device(level: int) -> int:
    """Convert ZCL level (0-254) to device brightness (10-1000)."""
    level = max(0, min(254, int(level)))
    return max(10, min(1000, round(10 + level * 990 / 254)))


def _current_level_254(endpoint: Any) -> int:
    """Get current level from endpoint, default to full brightness only if unset."""
    try:
        lvl = endpoint.level.get("current_level")
        if lvl is not None:
            return max(1, min(254, int(lvl)))
    except (AttributeError, KeyError, TypeError, ValueError):
        pass
    return 254


def _zcl_arg(pos: int, kw_name: str, args: tuple, kwargs: dict) -> Any | None:
    """Extract argument from args or kwargs."""
    if len(args) > pos:
        return args[pos]
    return kwargs.get(kw_name)


def _enhanced_hue_to_hue_254(enhanced_hue: int) -> int:
    """Convert enhanced hue (0-65535) to standard hue (0-254)."""
    return max(0, min(254, int(round(int(enhanced_hue) * 254 / 65535))))


def _xy_to_hs_254(x: int, y: int) -> tuple[int, int]:
    """Convert XY color to HS (0-254 range)."""
    xf = x / 65536.0
    yf = y / 65536.0
    if yf < 1e-6:
        return 0, 0
    X = xf / yf
    Y = 1.0
    Z = (1.0 - xf - yf) / yf
    r = X * 1.656492 - Y * 0.354851 - Z * 0.255038
    g = -X * 0.707196 + Y * 1.655397 + Z * 0.036152
    b = X * 0.051713 - Y * 0.121364 + Z * 1.011530
    r = max(r, 0.0)
    g = max(g, 0.0)
    b = max(b, 0.0)
    mx = max(r, g, b)
    if mx < 1e-6:  # pragma: no cover
        return 0, 0
    r, g, b = r / mx, g / mx, b / mx
    h, s, _v = colorsys.rgb_to_hsv(r, g, b)
    return max(0, min(254, int(h * 254))), max(0, min(254, int(s * 254)))


# ---------------------------------------------------------------------------
# Tuya MCU Cluster
# ---------------------------------------------------------------------------


class SpiLedManufCluster(TuyaMCUCluster):
    """Tuya MCU cluster for WZ-SPI LED controller."""

    class AttributeDefs(TuyaMCUCluster.AttributeDefs):
        """Attribute definitions."""

        work_mode: Final = ZCLAttributeDef(
            id=0xEF02, type=WorkMode, access="rw", is_manufacturer_specific=True
        )
        lightpixel_number_set: Final = ZCLAttributeDef(
            id=0xEF35, type=t.uint16_t, access="rw", is_manufacturer_specific=True
        )
        light_bead_sequence: Final = ZCLAttributeDef(
            id=0xEF65,
            type=LightBeadSequence,
            access="rw",
            is_manufacturer_specific=True,
        )
        chip_type: Final = ZCLAttributeDef(
            id=0xEF66, type=ChipType, access="rw", is_manufacturer_specific=True
        )

    dp_to_attribute: dict[int, DPToAttributeMapping | list[DPToAttributeMapping]] = {
        1: DPToAttributeMapping(TuyaOnOffNM.ep_attribute, "on_off"),
        2: DPToAttributeMapping(
            TuyaMCUCluster.ep_attribute, "work_mode", converter=lambda x: WorkMode(x)
        ),
        3: DPToAttributeMapping(
            TuyaLevelControl.ep_attribute,
            "current_level",
            converter=_level_from_device,
            dp_converter=_level_to_device,
        ),
        53: DPToAttributeMapping(TuyaMCUCluster.ep_attribute, "lightpixel_number_set"),
        61: [
            DPToAttributeMapping(
                Color.ep_attribute, "current_hue", converter=_dp61_to_hue
            ),
            DPToAttributeMapping(
                Color.ep_attribute, "current_saturation", converter=_dp61_to_sat
            ),
        ],
        101: DPToAttributeMapping(
            TuyaMCUCluster.ep_attribute,
            "light_bead_sequence",
            converter=lambda x: LightBeadSequence(x),
        ),
        102: DPToAttributeMapping(
            TuyaMCUCluster.ep_attribute, "chip_type", converter=lambda x: ChipType(x)
        ),
    }

    data_point_handlers = {
        1: "_dp_2_attr_update",
        2: "_dp_2_attr_update",
        3: "_dp_2_attr_update",
        53: "_dp_2_attr_update",
        61: "_dp_2_attr_update",
        101: "_dp_2_attr_update",
        102: "_dp_2_attr_update",
    }

    async def send_color_hs(
        self,
        hue_254: int,
        sat_254: int,
        expect_reply: bool,
        manufacturer: int | t.uint16_t | None,
    ) -> None:
        """Send HS color to device."""
        ep = self.endpoint
        dps: list[TuyaDatapointData] = []

        # Turn on if off
        if not ep.on_off.get("on_off", False):
            dps.append(TuyaDatapointData(dp=1, data=TuyaData(True)))

        # Switch to colour mode
        if self.get("work_mode") != WorkMode.colour:
            dps.append(TuyaDatapointData(dp=2, data=TuyaData(WorkMode.colour)))

        # Set brightness
        dps.append(
            TuyaDatapointData(
                dp=3, data=TuyaData(_level_to_device(_current_level_254(ep)))
            )
        )

        # Convert hue/sat to RGB, swap R↔G to compensate for GRB bead order,
        # then convert back to HSV for the device payload.
        h_norm = hue_254 / 254.0
        s_norm = sat_254 / 254.0
        r, g, b = colorsys.hsv_to_rgb(h_norm, s_norm, 1.0)
        r, g = g, r  # GRB compensation
        h_new, s_new, _ = colorsys.rgb_to_hsv(r, g, b)
        h_deg = int(h_new * 360)
        s_1000 = int(s_new * 1000)

        # Send color payload — use actual current brightness in V component
        val_1000 = _level_to_device(_current_level_254(ep))
        dps.append(
            TuyaDatapointData(
                dp=61, data=TuyaData(_dp61_payload(h_deg, s_1000, val_1000))
            )
        )

        cmd = TuyaCommand(
            status=0,
            tsn=ep.device.application.get_sequence(),
            datapoints=dps,
        )
        await self.command(
            TUYA_SET_DATA, cmd, expect_reply=expect_reply, manufacturer=manufacturer
        )

        # Update attributes
        self.update_attribute("work_mode", WorkMode.colour)
        lc = ep.light_color
        lc.update_attribute("current_hue", hue_254)
        lc.update_attribute("current_saturation", sat_254)
        lc.update_attribute("color_mode", Color.ColorMode.Hue_and_saturation)


# ---------------------------------------------------------------------------
# Color Cluster
# ---------------------------------------------------------------------------


class SpiLedColorCluster(Color, TuyaLocalCluster):
    """Color cluster for WZ-SPI with HS color support."""

    _CONSTANT_ATTRIBUTES = {
        Color.AttributeDefs.color_capabilities.id: Color.ColorCapabilities.Hue_and_saturation
        | Color.ColorCapabilities.Enhanced_hue
        | Color.ColorCapabilities.XY_attributes,
    }

    async def command(
        self,
        command_id: foundation.GeneralCommand | int | t.uint8_t,
        *args: Any,
        manufacturer: int | t.uint16_t | None = None,
        expect_reply: bool = True,
        tsn: int | t.uint8_t | None = None,
        **kwargs: Any,
    ) -> Any:
        """Handle color commands."""
        mcu: SpiLedManufCluster = self.endpoint.tuya_manufacturer
        dr = foundation.GENERAL_COMMANDS[
            foundation.GeneralCommand.Default_Response
        ].schema
        cid = int(command_id)

        # move_to_hue_and_saturation
        if cid == Color.ServerCommandDefs.move_to_hue_and_saturation.id:
            hue = _zcl_arg(0, "hue", args, kwargs)
            sat = _zcl_arg(1, "saturation", args, kwargs)
            if hue is None or sat is None:
                return dr(command_id=command_id, status=foundation.Status.FAILURE)
            await mcu.send_color_hs(int(hue), int(sat), expect_reply, manufacturer)
            return dr(command_id=command_id, status=foundation.Status.SUCCESS)

        # move_to_hue
        if cid == Color.ServerCommandDefs.move_to_hue.id:
            hue = _zcl_arg(0, "hue", args, kwargs)
            if hue is None:
                return dr(command_id=command_id, status=foundation.Status.FAILURE)
            sat = int(self.get("current_saturation") or 254)
            await mcu.send_color_hs(int(hue), sat, expect_reply, manufacturer)
            return dr(command_id=command_id, status=foundation.Status.SUCCESS)

        # move_to_saturation
        if cid == Color.ServerCommandDefs.move_to_saturation.id:
            sat = _zcl_arg(0, "saturation", args, kwargs)
            if sat is None:
                return dr(command_id=command_id, status=foundation.Status.FAILURE)
            hue = int(self.get("current_hue") or 0)
            await mcu.send_color_hs(hue, int(sat), expect_reply, manufacturer)
            return dr(command_id=command_id, status=foundation.Status.SUCCESS)

        # move_to_color (XY)
        if cid == Color.ServerCommandDefs.move_to_color.id:
            cx = _zcl_arg(0, "color_x", args, kwargs)
            cy = _zcl_arg(1, "color_y", args, kwargs)
            if cx is None or cy is None:
                return dr(command_id=command_id, status=foundation.Status.FAILURE)
            h, s = _xy_to_hs_254(int(cx), int(cy))
            await mcu.send_color_hs(h, s, expect_reply, manufacturer)
            self.update_attribute("current_x", int(cx))
            self.update_attribute("current_y", int(cy))
            return dr(command_id=command_id, status=foundation.Status.SUCCESS)

        # enhanced_move_to_hue_and_saturation
        if cid == Color.ServerCommandDefs.enhanced_move_to_hue_and_saturation.id:
            eh = _zcl_arg(0, "enhanced_hue", args, kwargs)
            sat = _zcl_arg(1, "saturation", args, kwargs)
            if eh is None or sat is None:
                return dr(command_id=command_id, status=foundation.Status.FAILURE)
            h254 = _enhanced_hue_to_hue_254(int(eh))
            await mcu.send_color_hs(h254, int(sat), expect_reply, manufacturer)
            self.update_attribute("enhanced_current_hue", int(eh))
            return dr(command_id=command_id, status=foundation.Status.SUCCESS)

        # stop_move_step — acknowledge only
        if cid == Color.ServerCommandDefs.stop_move_step.id:
            return dr(command_id=command_id, status=foundation.Status.SUCCESS)

        self.warning("Unsupported color command: %s", command_id)
        return dr(command_id=command_id, status=foundation.Status.UNSUP_CLUSTER_COMMAND)


# ---------------------------------------------------------------------------
# Device Class
# ---------------------------------------------------------------------------


class EnchantedSpiLed(CustomDeviceV2, BaseEnchantedDevice):
    """Enchanted device class for WZ-SPI."""

    tuya_spell_read_attributes = True
    tuya_spell_data_query = False


# ---------------------------------------------------------------------------
# Quirk Registration
# ---------------------------------------------------------------------------

(
    QuirkBuilder("_TZE204_8fffc3kb", "TS0601")
    .also_applies_to("_TZE284_gt5al3bl", "TS0601")
    .device_class(EnchantedSpiLed)
    .replaces_endpoint(
        1, profile_id=zha.PROFILE_ID, device_type=zha.DeviceType.EXTENDED_COLOR_LIGHT
    )
    .replaces(SpiLedManufCluster)
    .adds(TuyaOnOffNM)
    .adds(TuyaLevelControl)
    .adds(SpiLedColorCluster)
    .number(
        attribute_name="lightpixel_number_set",
        cluster_id=TUYA_CLUSTER_ID,
        min_value=10,
        max_value=1000,
        step=1,
        translation_key="lightpixel_number_set",
        fallback_name="LED count",
        entity_type=EntityType.CONFIG,
    )
    .enum(
        attribute_name="light_bead_sequence",
        enum_class=LightBeadSequence,
        cluster_id=TUYA_CLUSTER_ID,
        translation_key="light_bead_sequence",
        fallback_name="LED strip order",
        entity_type=EntityType.CONFIG,
    )
    .enum(
        attribute_name="chip_type",
        enum_class=ChipType,
        cluster_id=TUYA_CLUSTER_ID,
        translation_key="chip_type",
        fallback_name="IC type",
        entity_type=EntityType.CONFIG,
    )
    .skip_configuration()
    .add_to_registry()
)
