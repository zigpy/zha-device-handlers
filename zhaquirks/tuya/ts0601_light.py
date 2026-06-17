"""Tuya TS0601 SPI / addressable RGB(W) LED strip controllers.

Currently supports the Gledopto GL-SPI-206P (and its hardware variant), a
Tuya-MCU (cluster 0xEF00) pixel LED controller. Unlike standard ZCL lights
these devices expose all functionality through Tuya datapoints, so a normal
``QuirkBuilder`` cannot produce a usable light.

This quirk assembles a proper Home Assistant light (on/off + brightness + color
picker + color temperature) by mapping the Tuya datapoints onto local
``OnOff``/``LevelControl``/``Color`` clusters and translating the ZCL light
*commands* HA sends back into datapoint writes.

The ``zha`` light platform only implements XY and color-temp color modes (no
Hue/Saturation), so the Color cluster advertises XY and converts the incoming
CIE xy color into the device's native HSV datapoint payload.

Datapoint map (verified against zigbee-herdsman-converters ``gledopto.ts``)::

    DP   1  on/off               -> OnOff.on_off
    DP   2  work_mode (enum)     -> manufacturer cluster (drives color mode)
    DP   3  brightness 10-1000   -> LevelControl.current_level
    DP   4  color_temp 0-1000    -> Color.color_temperature  (0=warm, 1000=cold)
    DP   7  countdown (seconds)  -> number (config)
    DP  53  pixel count 10-1000  -> number (config)
    DP  61  HSV color (raw)      -> Color.current_hue + current_saturation
    DP 101  led color order      -> select (config)
    DP 102  led chip type        -> select (config)
    DP 103  do not disturb       -> switch

The device does not report color/brightness state back (no Tuya "report" for
these DPs), so the light state is command-optimistic: the local clusters are
updated when a command is issued.
"""

import colorsys
from typing import Any

from zigpy.profiles import zha
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.lighting import Color

from zhaquirks.tuya import TUYA_MCU_COMMAND, TuyaLocalCluster
from zhaquirks.tuya.builder import TuyaQuirkBuilder
from zhaquirks.tuya.mcu import (
    DPToAttributeMapping,
    TuyaClusterData,
    TuyaLevelControl,
    TuyaMCUCluster,
    TuyaOnOffNM,
)

# --- Scaling constants -------------------------------------------------------

ZCL_LEVEL_MAX = 254  # ZCL brightness/hue/saturation use 0-254
TUYA_HUE_MAX = 360  # DP 61 hue is degrees 0-360
TUYA_SAT_MAX = 1000  # DP 61 saturation is 0-1000
TUYA_VALUE = 1000  # DP 61 value (brightness) is fixed; brightness lives on DP 3
TUYA_BRIGHTNESS_MIN = 10  # DP 3 lower bound
TUYA_BRIGHTNESS_MAX = 1000  # DP 3 upper bound
TUYA_COLOR_TEMP_MAX = 1000  # DP 4: 0=warm .. 1000=cold

# Color temperature range exposed to HA. The strip simulates white via DP 4,
# so the exact Kelvin endpoints are nominal.
COLOR_TEMP_MIN_MIREDS = 153  # ~6535 K (cold)
COLOR_TEMP_MAX_MIREDS = 500  # 2000 K (warm)

# Fixed header of the 11-byte DP 61 payload, taken verbatim from the Z2M
# converter: [type, transition, 0x01, 0x14, 0x00].
_COLOR_HEADER = bytes((0x00, 0x01, 0x01, 0x14, 0x00))


def _clamp(value: float, low: int, high: int) -> int:
    """Round and clamp a value into an inclusive integer range."""
    return max(low, min(high, round(value)))


# --- DP 61 (HSV color) encode / decode --------------------------------------


def encode_color(hue: int | None, saturation: int | None) -> t.Bytes:
    """Build the 11-byte Tuya HSV payload from ZCL hue/saturation (0-254)."""
    h = _clamp((hue or 0) * TUYA_HUE_MAX / ZCL_LEVEL_MAX, 0, TUYA_HUE_MAX)
    s = _clamp((saturation or 0) * TUYA_SAT_MAX / ZCL_LEVEL_MAX, 0, TUYA_SAT_MAX)
    v = TUYA_VALUE
    return t.Bytes(
        _COLOR_HEADER
        + bytes(
            (
                (h >> 8) & 0xFF,
                h & 0xFF,
                (s >> 8) & 0xFF,
                s & 0xFF,
                (v >> 8) & 0xFF,
                v & 0xFF,
            )
        )
    )


def decode_hue(raw: bytes) -> int:
    """Extract ZCL hue (0-254) from a Tuya HSV payload."""
    if len(raw) < 11:
        return 0
    h = (raw[5] << 8) | raw[6]
    return _clamp(h * ZCL_LEVEL_MAX / TUYA_HUE_MAX, 0, ZCL_LEVEL_MAX)


def decode_saturation(raw: bytes) -> int:
    """Extract ZCL saturation (0-254) from a Tuya HSV payload."""
    if len(raw) < 11:
        return 0
    s = (raw[7] << 8) | raw[8]
    return _clamp(s * ZCL_LEVEL_MAX / TUYA_SAT_MAX, 0, ZCL_LEVEL_MAX)


def _gamma(c: float) -> float:
    """Apply sRGB gamma companding to a linear channel value."""
    return 12.92 * c if c <= 0.0031308 else 1.055 * (c ** (1 / 2.4)) - 0.055


def xy_to_hs(color_x: int, color_y: int) -> tuple[int, int]:
    """Convert ZCL CIE xy (uint16) to ZCL hue/saturation (0-254).

    HA/zha represents color as CIE xy; the device wants hue/saturation. We map
    xy -> linear sRGB -> gamma sRGB -> HSV, ignoring brightness (handled on DP 3).
    """
    x = color_x / 65535
    y = color_y / 65535
    if y <= 0:
        return 0, 0
    big_x = x / y
    big_z = (1.0 - x - y) / y
    r = big_x * 3.2406 - 1.5372 - big_z * 0.4986
    g = -big_x * 0.9689 + 1.8758 + big_z * 0.0415
    b = big_x * 0.0557 - 0.2040 + big_z * 1.0570
    r, g, b = (max(0.0, c) for c in (r, g, b))
    peak = max(r, g, b) or 1.0
    r, g, b = (_gamma(c / peak) for c in (r, g, b))
    hue, sat, _val = colorsys.rgb_to_hsv(
        min(1.0, max(0.0, r)), min(1.0, max(0.0, g)), min(1.0, max(0.0, b))
    )
    return round(hue * ZCL_LEVEL_MAX), round(sat * ZCL_LEVEL_MAX)


# --- DP 3 (brightness) scaling ----------------------------------------------


def level_to_dp(level: int) -> int:
    """Convert ZCL level (0-254) to Tuya brightness (10-1000)."""
    span = TUYA_BRIGHTNESS_MAX - TUYA_BRIGHTNESS_MIN
    return _clamp(
        TUYA_BRIGHTNESS_MIN + level * span / ZCL_LEVEL_MAX,
        TUYA_BRIGHTNESS_MIN,
        TUYA_BRIGHTNESS_MAX,
    )


def dp_to_level(value: int) -> int:
    """Convert Tuya brightness (10-1000) to ZCL level (1-254)."""
    span = TUYA_BRIGHTNESS_MAX - TUYA_BRIGHTNESS_MIN
    return _clamp(
        (value - TUYA_BRIGHTNESS_MIN) * ZCL_LEVEL_MAX / span, 1, ZCL_LEVEL_MAX
    )


# --- DP 4 (color temperature) scaling ---------------------------------------


def mireds_to_dp(mireds: int) -> int:
    """Convert ZCL mireds to Tuya color temp (0=warm .. 1000=cold)."""
    span = COLOR_TEMP_MAX_MIREDS - COLOR_TEMP_MIN_MIREDS
    return _clamp(
        (COLOR_TEMP_MAX_MIREDS - mireds) * TUYA_COLOR_TEMP_MAX / span,
        0,
        TUYA_COLOR_TEMP_MAX,
    )


def dp_to_mireds(value: int) -> int:
    """Convert Tuya color temp (0=warm .. 1000=cold) to ZCL mireds."""
    span = COLOR_TEMP_MAX_MIREDS - COLOR_TEMP_MIN_MIREDS
    return _clamp(
        COLOR_TEMP_MAX_MIREDS - value * span / TUYA_COLOR_TEMP_MAX,
        COLOR_TEMP_MIN_MIREDS,
        COLOR_TEMP_MAX_MIREDS,
    )


# --- Enums ------------------------------------------------------------------


class TuyaWorkMode(t.enum8):
    """Operating mode (DP 2)."""

    white = 0x00
    colour = 0x01
    scene = 0x02
    music = 0x03


class TuyaLightBeadSequence(t.enum8):
    """RGB(W) channel wiring order (DP 101)."""

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


class TuyaChipType(t.enum8):
    """LED driver chip (DP 102)."""

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


# --- Custom Color cluster ----------------------------------------------------


class TuyaColorControl(Color, TuyaLocalCluster):
    """Tuya MCU Color cluster.

    Translates ZCL color commands (XY + color temperature) into Tuya datapoint
    writes. XY color is converted to the device's HSV payload (DP 61).
    """

    # zha's light platform only implements XY and color-temp color modes (it has
    # no Hue/Saturation path), so advertise XY even though the device speaks HSV.
    _CONSTANT_ATTRIBUTES = {
        Color.AttributeDefs.color_capabilities.id: (
            Color.ColorCapabilities.XY_attributes
            | Color.ColorCapabilities.Color_temperature
        ),
        Color.AttributeDefs.color_temp_physical_min.id: COLOR_TEMP_MIN_MIREDS,
        Color.AttributeDefs.color_temp_physical_max.id: COLOR_TEMP_MAX_MIREDS,
    }

    def _send_mcu(
        self,
        cluster_name: str,
        cluster_attr: str,
        attr_value: Any,
        manufacturer: int | None,
    ) -> None:
        """Fire a Tuya MCU command to write a single attribute -> datapoint.

        Sent fire-and-forget (``expect_reply=False``). ZHA invokes light commands
        with ``expect_reply=True``, which makes every datapoint write block on the
        device's application-level response; under a streamed colour/brightness
        drag those waits queue up, stall, then flush in a batch. The frames are
        still APS/MAC acknowledged, so we lose nothing by not awaiting the reply.
        This matches how Tuya convenience entities (and Z2M) send datapoints.
        """
        cluster_data = TuyaClusterData(
            endpoint_id=self.endpoint.endpoint_id,
            cluster_name=cluster_name,
            cluster_attr=cluster_attr,
            attr_value=attr_value,
            expect_reply=False,
            manufacturer=manufacturer,
        )
        self.endpoint.device.command_bus.listener_event(
            TUYA_MCU_COMMAND,
            cluster_data,
        )

    def _ensure_work_mode(self, mode: "TuyaWorkMode", manufacturer: int | None) -> None:
        """Send the work_mode DP only when it differs from the current value.

        The device keeps its work mode until changed, so resending it on every
        streamed colour/brightness update just floods the MCU and causes dropped
        frames. Mirrors the Z2M behaviour of only switching mode when needed.
        """
        manuf = getattr(self.endpoint, TuyaMCUCluster.ep_attribute, None)
        if manuf is not None and manuf.get("work_mode") == mode:
            return
        self._send_mcu(TuyaMCUCluster.ep_attribute, "work_mode", mode, manufacturer)

    def _ok(self, command_id: int) -> Any:
        """Build a successful Default Response for a handled command."""
        return foundation.GENERAL_COMMANDS[
            foundation.GeneralCommand.Default_Response
        ].schema(command_id=command_id, status=foundation.Status.SUCCESS)

    @staticmethod
    def _param(args, kwargs, name: str, index: int, default: int) -> int:
        """Read a command argument by schema name (kwargs) or position (args).

        ZHA may invoke command methods with either keyword or positional
        arguments depending on version, so both forms must be supported.
        """
        if name in kwargs:
            return kwargs[name]
        if len(args) > index:
            return args[index]
        return default

    async def command(
        self,
        command_id: foundation.GeneralCommand | int | t.uint8_t,
        *args,
        manufacturer: int | t.uint16_t | None = None,
        expect_reply: bool = True,
        tsn: int | t.uint8_t | None = None,
        **kwargs: Any,
    ):
        """Override ZCL color commands and forward them to the MCU."""
        self.debug(
            "Sending Tuya Color command %x, args=%s, kwargs=%s",
            command_id,
            args,
            kwargs,
        )

        attrs = Color.AttributeDefs
        cmds = Color.ServerCommandDefs

        # XY color -> colour mode + DP 61
        if command_id == cmds.move_to_color.id:
            color_x = self._param(
                args, kwargs, "color_x", 0, self.get(attrs.current_x.id, 0)
            )
            color_y = self._param(
                args, kwargs, "color_y", 1, self.get(attrs.current_y.id, 0)
            )
            hue, saturation = xy_to_hs(color_x, color_y)

            # Optimistic state: zha reads current_x/current_y for display, while
            # current_hue/current_saturation carry the values used to build DP 61.
            self.update_attribute(attrs.current_x.name, color_x)
            self.update_attribute(attrs.current_y.name, color_y)
            self.update_attribute(attrs.current_saturation.name, saturation)
            self.update_attribute(attrs.current_hue.name, hue)
            self.update_attribute(attrs.color_mode.name, Color.ColorMode.X_and_Y)

            # switch the strip to colour mode only if needed, then push the colour
            self._ensure_work_mode(TuyaWorkMode.colour, manufacturer)
            # firing current_hue rebuilds DP 61 from hue + current_saturation
            self._send_mcu(self.ep_attribute, attrs.current_hue.name, hue, manufacturer)
            return self._ok(command_id)

        # Color temperature -> white mode + DP 4
        if command_id == cmds.move_to_color_temp.id:
            mireds = self._param(
                args,
                kwargs,
                "color_temp_mireds",
                0,
                self.get(attrs.color_temperature.id, COLOR_TEMP_MIN_MIREDS),
            )
            self.update_attribute(attrs.color_temperature.name, mireds)
            self.update_attribute(
                attrs.color_mode.name, Color.ColorMode.Color_temperature
            )
            # switch to white mode only if needed, then push the colour temp
            self._ensure_work_mode(TuyaWorkMode.white, manufacturer)
            self._send_mcu(
                self.ep_attribute, attrs.color_temperature.name, mireds, manufacturer
            )
            return self._ok(command_id)

        self.warning("Unsupported color command_id: %s", command_id)
        return foundation.GENERAL_COMMANDS[
            foundation.GeneralCommand.Default_Response
        ].schema(command_id=command_id, status=foundation.Status.UNSUP_CLUSTER_COMMAND)


class TuyaSpiOnOff(TuyaOnOffNM):
    """OnOff cluster that sends fire-and-forget.

    The device takes seconds to send its application-level response to a
    datapoint write. With zigpy's per-device concurrency of 1 and
    ``expect_reply=True``, each on/off command holds the single request slot
    until that response (or a ~4 s timeout), stalling every other command --
    including unrelated config writes -- behind it. ``expect_reply=False``
    releases the slot immediately; device state still arrives via DP reports.
    """

    async def command(
        self,
        command_id: foundation.GeneralCommand | int | t.uint8_t,
        *args,
        expect_reply: bool = True,
        **kwargs: Any,
    ):
        """Forward to the base command with ``expect_reply`` forced off."""
        return await super().command(command_id, *args, expect_reply=False, **kwargs)


class TuyaSpiLevelControl(TuyaLevelControl):
    """Level cluster that sends brightness fire-and-forget (see TuyaSpiOnOff)."""

    async def command(
        self,
        command_id: foundation.GeneralCommand | int | t.uint8_t,
        *args,
        expect_reply: bool = True,
        **kwargs: Any,
    ):
        """Forward to the base command with ``expect_reply`` forced off."""
        return await super().command(command_id, *args, expect_reply=False, **kwargs)


# --- Quirk -------------------------------------------------------------------

(
    TuyaQuirkBuilder("_TZE284_gt5al3bl", "TS0601")
    .applies_to("_TZE204_8fffc3kb", "TS0601")
    # DP 1 - on/off (fire-and-forget; see TuyaSpiOnOff)
    .tuya_onoff(dp_id=1, onoff_cfg=TuyaSpiOnOff)
    # DP 3 - brightness -> LevelControl
    .tuya_dp(
        dp_id=3,
        ep_attribute=TuyaSpiLevelControl.ep_attribute,
        attribute_name="current_level",
        converter=dp_to_level,
        dp_converter=level_to_dp,
    )
    .adds(TuyaSpiLevelControl)
    # DP 4 - color temperature -> Color
    .tuya_dp(
        dp_id=4,
        ep_attribute=TuyaColorControl.ep_attribute,
        attribute_name=Color.AttributeDefs.color_temperature.name,
        converter=dp_to_mireds,
        dp_converter=mireds_to_dp,
    )
    # DP 61 - HSV color (single DP -> hue + saturation)
    .tuya_dp_multi(
        dp_id=61,
        attribute_mapping=[
            DPToAttributeMapping(
                TuyaColorControl.ep_attribute,
                Color.AttributeDefs.current_hue.name,
                converter=decode_hue,
            ),
            DPToAttributeMapping(
                TuyaColorControl.ep_attribute,
                Color.AttributeDefs.current_saturation.name,
                converter=decode_saturation,
            ),
        ],
        dp_converter=encode_color,
    )
    .adds(TuyaColorControl)
    # Present endpoint 1 as a color light so HA builds the right entity
    .replaces_endpoint(1, device_type=zha.DeviceType.EXTENDED_COLOR_LIGHT)
    # DP 2 - work mode (also driven by the colour/white commands above)
    .tuya_enum(
        dp_id=2,
        attribute_name="work_mode",
        enum_class=TuyaWorkMode,
        translation_key="work_mode",
        fallback_name="Work mode",
    )
    # DP 7 - countdown timer
    .tuya_number(
        dp_id=7,
        attribute_name="countdown",
        type=t.uint32_t,
        min_value=0,
        max_value=86400,
        step=1,
        translation_key="countdown",
        fallback_name="Countdown",
    )
    # DP 53 - pixel count
    .tuya_number(
        dp_id=53,
        attribute_name="pixel_count",
        type=t.uint16_t,
        min_value=10,
        max_value=1000,
        step=1,
        translation_key="pixel_count",
        fallback_name="Pixel count",
    )
    # DP 101 - LED color order
    .tuya_enum(
        dp_id=101,
        attribute_name="light_bead_sequence",
        enum_class=TuyaLightBeadSequence,
        translation_key="light_bead_sequence",
        fallback_name="LED color order",
    )
    # DP 102 - LED chip type
    .tuya_enum(
        dp_id=102,
        attribute_name="chip_type",
        enum_class=TuyaChipType,
        translation_key="chip_type",
        fallback_name="Chip type",
    )
    # DP 103 - do not disturb
    .tuya_switch(
        dp_id=103,
        attribute_name="do_not_disturb",
        translation_key="do_not_disturb",
        fallback_name="Do not disturb",
    )
    .skip_configuration()
    .add_to_registry()
)
