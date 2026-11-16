"""ZHA quirk for Lidl Melinera HG06467 smart LED string lights.

Device:
    manufacturer: _TZE200_s8gkrkxk
    model:        TS0601

Protocol (Tuya MCU cluster 0xEF00), as documented by zigbee-herdsman-converters
(src/lib/lidl.ts) and ptc/Melinera_HG06467:

    DP1 = power (bool). The physical button reports only this DP.
    DP2 = mode (enum): 0 white, 1 color, 2 effect
    DP3 = white brightness (value): 0..1000
    DP4 = color temperature (value): 0..1000 (not used by Z2M; kept experimental)
    DP5 = color (string): HHHHSSSSBBBB, hex hue 0..359, sat 0..1000, bri 0..1000
    DP6 = effect (string): EE SS [RRGGBB ...]
          EE = effect id, hex 00..0f
          SS = speed, DECIMAL 00..64
          RRGGBB = up to six palette colors, hex

Color handling:
    ZHA drives colour lights only through CIE xy. Home Assistant converts the
    colour wheel's hue/saturation to xy with its "Wide RGB D65" matrices
    (homeassistant.util.color). This quirk uses exactly the inverse of those
    matrices, so the hue/saturation sent to the string is the one picked in the
    UI - the same values Zigbee2MQTT sends - instead of being shifted by an
    sRGB/Wide RGB matrix mismatch.

Exposed in Home Assistant:
    - light: on/off, brightness, colour (xy), colour temperature
    - select "Effect": 16 built-in effects
    - number "Effect speed": 0..100 %, kept for the next effect when not in
      effect mode (as in Zigbee2MQTT)
    - select "Light mode": white / color / effect
"""

from __future__ import annotations

import colorsys
from typing import Any

import zigpy.types as t
from zigpy.typing import UNDEFINED, UndefinedType
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import LevelControl, OnOff
from zigpy.zcl.clusters.lighting import Color

from zhaquirks.builder import EntityType
from zhaquirks.clusters import CustomCluster
from zhaquirks.tuya import TuyaCommand, TuyaDatapointData
from zhaquirks.tuya.builder import TuyaQuirkBuilder
from zhaquirks.tuya.mcu import DPToAttributeMapping, TuyaMCUCluster

TUYA_CLUSTER_ID = 0xEF00

DP_POWER = 1
DP_MODE = 2
DP_WHITE_BRIGHTNESS = 3
DP_COLOR_TEMP = 4
DP_COLOR = 5
DP_EFFECT = 6

COLOR_TEMP_MIN = 250  # mireds, coolest
COLOR_TEMP_MAX = 454  # mireds, warmest

DEFAULT_SPEED = 50  # percent
DEVICE_SPEED_MAX = 64


class LightMode(t.enum8):
    """DP2 operating mode."""

    White = 0x00
    Color = 0x01
    Effect = 0x02


class StringEffect(t.enum8):
    """DP6 built-in effects."""

    Steady = 0x00
    Snow = 0x01
    Rainbow = 0x02
    Snake = 0x03
    Twinkle = 0x04
    Firework = 0x05
    Horizontal_flag = 0x06
    Waves = 0x07
    Updown = 0x08
    Vintage = 0x09
    Fading = 0x0A
    Collide = 0x0B
    Strobe = 0x0C
    Sparkles = 0x0D
    Carnaval = 0x0E
    Glow = 0x0F


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


# --- colour conversion, mirroring homeassistant.util.color -----------------


def _srgb_to_linear(c: float) -> float:
    return ((c + 0.055) / 1.055) ** 2.4 if c > 0.04045 else c / 12.92


def _linear_to_srgb(c: float) -> float:
    return 12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055


def hs_to_xy(hue_deg: float, sat_1000: float) -> tuple[float, float]:
    """Device hue/saturation -> CIE xy, as HA's color_hs_to_xy does."""
    r, g, b = colorsys.hsv_to_rgb(
        (hue_deg % 360) / 360, _clamp(sat_1000, 0, 1000) / 1000, 1.0
    )
    r, g, b = _srgb_to_linear(r), _srgb_to_linear(g), _srgb_to_linear(b)
    x_ = r * 0.664511 + g * 0.154324 + b * 0.162028
    y_ = r * 0.283881 + g * 0.668433 + b * 0.047685
    z_ = r * 0.000088 + g * 0.072310 + b * 0.986039
    total = x_ + y_ + z_
    if total <= 0:
        return (0.0, 0.0)
    return (x_ / total, y_ / total)


def xy_to_hs(x: float, y: float) -> tuple[float, float]:
    """CIE xy -> device hue (deg) and saturation (0..1000), inverse of HA's conversion."""
    if y <= 0:
        y = 1e-11
    big_y = 1.0
    big_x = (big_y / y) * x
    big_z = (big_y / y) * (1 - x - y)
    r = big_x * 1.656492 - big_y * 0.354851 - big_z * 0.255038
    g = -big_x * 0.707196 + big_y * 1.655397 + big_z * 0.036152
    b = big_x * 0.051713 - big_y * 0.121364 + big_z * 1.011530
    r, g, b = (max(0.0, _linear_to_srgb(c)) for c in (r, g, b))
    peak = max(r, g, b)
    if peak > 1:
        r, g, b = r / peak, g / peak, b / peak
    if peak <= 0:
        return (0.0, 0.0)
    h, s, _ = colorsys.rgb_to_hsv(r, g, b)
    return (h * 360 % 360, s * 1000)


# --- DP converters ------------------------------------------------------------


def parse_hsb(value: Any) -> tuple[int, int, int]:
    """Decode the DP5 HHHHSSSSBBBB string (white at full brightness if malformed)."""
    text = str(value)
    try:
        hue, sat, bri = (int(text[i : i + 4], 16) for i in (0, 4, 8))
    except ValueError:
        return (0, 0, 1000)
    return (hue % 360, int(_clamp(sat, 0, 1000)), int(_clamp(bri, 0, 1000)))


def encode_hsb(hue_deg: float, sat_1000: float, bri_1000: float) -> str:
    """Encode hue/saturation/brightness as the DP5 string."""
    return (
        f"{round(hue_deg) % 360:04x}"
        f"{round(_clamp(sat_1000, 0, 1000)):04x}"
        f"{round(_clamp(bri_1000, 0, 1000)):04x}"
    )


def level_to_1000(level: int | None) -> int:
    """Convert a ZCL level 0..254 to the device range 0..1000."""
    return round(_clamp(254 if level is None else int(level), 0, 254) * 1000 / 254)


def to_level(value_1000: Any) -> int:
    """Convert a device brightness 0..1000 to a ZCL level 0..254."""
    return round(_clamp(int(value_1000), 0, 1000) * 254 / 1000)


def dp5_to_x(value: Any) -> int:
    """Convert DP5 to ZCL current_x."""
    hue, sat, _ = parse_hsb(value)
    return round(hs_to_xy(hue, sat)[0] * 65535)


def dp5_to_y(value: Any) -> int:
    """Convert DP5 to ZCL current_y."""
    hue, sat, _ = parse_hsb(value)
    return round(hs_to_xy(hue, sat)[1] * 65535)


def dp5_to_level(value: Any) -> int:
    """Convert DP5 brightness to a ZCL level."""
    return to_level(parse_hsb(value)[2])


def dp4_to_mireds(value: Any) -> int:
    """Device 0 = warmest, 1000 = coolest."""
    v = _clamp(int(value), 0, 1000)
    return round(COLOR_TEMP_MAX - v * (COLOR_TEMP_MAX - COLOR_TEMP_MIN) / 1000)


def mireds_to_dp4(mireds: int) -> int:
    """Convert mireds to the DP4 range (0 = warmest)."""
    m = _clamp(int(mireds), COLOR_TEMP_MIN, COLOR_TEMP_MAX)
    return round((COLOR_TEMP_MAX - m) * 1000 / (COLOR_TEMP_MAX - COLOR_TEMP_MIN))


def dp2_to_color_mode(value: Any) -> Color.ColorMode:
    """Map the DP2 mode to the ZCL colour mode."""
    if int(value) == LightMode.White:
        return Color.ColorMode.Color_temperature
    return Color.ColorMode.X_and_Y


def dp6_to_effect(value: Any) -> StringEffect:
    """Read the effect id from DP6."""
    try:
        return StringEffect(int(str(value)[0:2], 16))
    except ValueError:
        return StringEffect.Steady


def dp6_to_speed(value: Any) -> int:
    """Two DECIMAL digits 0..64 -> percent."""
    try:
        raw = int(str(value)[2:4], 10)
    except ValueError:
        return DEFAULT_SPEED
    return round(_clamp(raw, 0, DEVICE_SPEED_MAX) * 100 / DEVICE_SPEED_MAX)


def dp6_to_palette(value: Any) -> str:
    """Palette colours as reported, kept so speed/effect changes don't drop them."""
    text = str(value)[4:].lower()
    text = text[: len(text) - len(text) % 6][: 6 * 6]
    return text if all(c in "0123456789abcdef" for c in text) else ""


def effect_to_dp6(effect: Any, speed: Any, palette: Any) -> str:
    """Build DP6 from the effect, speed (percent) and stored palette."""
    effect_id = int(StringEffect.Steady if effect is None else effect)
    percent = DEFAULT_SPEED if speed is None else _clamp(int(speed), 0, 100)
    device_speed = round(percent * DEVICE_SPEED_MAX / 100)
    return f"{effect_id:02x}{device_speed:02d}{palette or ''}"


# --- clusters -------------------------------------------------------------------


class MelineraTuyaCluster(TuyaMCUCluster):
    """Tuya MCU cluster that stores the effect speed until effect mode is used.

    Writing DP6 always switches the string into effect mode, so - as in
    Zigbee2MQTT - a speed change outside effect mode is only remembered.
    """

    async def write_attributes(
        self,
        attributes: dict[str | int | foundation.ZCLAttributeDef, Any],
        manufacturer: int | UndefinedType | None = UNDEFINED,
        **kwargs,
    ) -> list[list[foundation.WriteAttributesStatusRecord]]:
        """Store the effect speed locally unless the string is in effect mode."""
        remaining: dict[str | int | foundation.ZCLAttributeDef, Any] = {}
        in_effect_mode = self.get("light_mode") == LightMode.Effect
        for key, value in attributes.items():
            attr = self.find_attribute(key)
            if attr.name == "effect_speed" and not in_effect_mode:
                self.update_attribute(attr.name, attr.type(value))
            else:
                remaining[key] = value
        if remaining:
            return await super().write_attributes(
                remaining, manufacturer=manufacturer, **kwargs
            )
        return [[foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)]]


class MelineraColorCluster(CustomCluster, Color):
    """Translate ZCL xy / colour temperature commands into Tuya datapoints."""

    _CONSTANT_ATTRIBUTES = {
        Color.AttributeDefs.color_capabilities.id: (
            Color.ColorCapabilities.XY_attributes
            | Color.ColorCapabilities.Color_temperature
        ),
        Color.AttributeDefs.color_temp_physical_min.id: COLOR_TEMP_MIN,
        Color.AttributeDefs.color_temp_physical_max.id: COLOR_TEMP_MAX,
    }

    async def read_attributes(self, attributes, **kwargs):
        """Serve reads from the cache; the device's Color cluster lacks the Tuya state."""
        kwargs.pop("allow_cache", None)
        kwargs.pop("only_cache", None)
        return await super().read_attributes(
            attributes, allow_cache=True, only_cache=True, **kwargs
        )

    @property
    def _tuya(self) -> MelineraTuyaCluster:
        return self.endpoint.tuya_manufacturer

    async def _send(self, dp: int, value: Any) -> None:
        await self._tuya.command(
            self._tuya.mcu_write_command,
            TuyaCommand(
                status=0,
                tsn=self.endpoint.device.application.get_sequence(),
                datapoints=[TuyaDatapointData(dp, value)],
            ),
            expect_reply=False,
        )

    def _success(self, command_id):
        return foundation.GENERAL_COMMANDS[
            foundation.GeneralCommand.Default_Response
        ].schema(command_id=command_id, status=foundation.Status.SUCCESS)

    async def command(self, command_id, *args, **kwargs):
        """Handle xy and colour temperature commands via Tuya datapoints."""
        if command_id == Color.ServerCommandDefs.move_to_color.id:
            x = int(kwargs.get("color_x", args[0] if args else 0))
            y = int(kwargs.get("color_y", args[1] if len(args) > 1 else 0))
            hue, sat = xy_to_hs(x / 65535, y / 65535)
            level = self.endpoint.level.get(
                LevelControl.AttributeDefs.current_level.name
            )

            await self._send(DP_MODE, LightMode.Color)
            await self._send(DP_COLOR, encode_hsb(hue, sat, level_to_1000(level)))

            self._tuya.update_attribute("light_mode", LightMode.Color)
            self.update_attribute(Color.AttributeDefs.current_x.name, x)
            self.update_attribute(Color.AttributeDefs.current_y.name, y)
            self.update_attribute(
                Color.AttributeDefs.color_mode.name, Color.ColorMode.X_and_Y
            )
            return self._success(command_id)

        if command_id == Color.ServerCommandDefs.move_to_color_temp.id:
            mireds = int(
                kwargs.get("color_temp_mireds", args[0] if args else COLOR_TEMP_MAX)
            )
            await self._send(DP_MODE, LightMode.White)
            await self._send(DP_COLOR_TEMP, mireds_to_dp4(mireds))

            self._tuya.update_attribute("light_mode", LightMode.White)
            self.update_attribute(
                Color.AttributeDefs.color_temperature.name,
                int(_clamp(mireds, COLOR_TEMP_MIN, COLOR_TEMP_MAX)),
            )
            self.update_attribute(
                Color.AttributeDefs.color_mode.name,
                Color.ColorMode.Color_temperature,
            )
            return self._success(command_id)

        return await super().command(command_id, *args, **kwargs)


(
    TuyaQuirkBuilder("_TZE200_s8gkrkxk", "TS0601")
    .replaces(MelineraColorCluster)
    # Physical button: the string reports power only through DP1.
    .tuya_dp(
        dp_id=DP_POWER,
        ep_attribute=OnOff.ep_attribute,
        attribute_name=OnOff.AttributeDefs.on_off.name,
        converter=lambda v: t.Bool(bool(v)),
    )
    # Mode: select entity, and keeps the light's colour mode in sync.
    .tuya_attribute(
        dp_id=DP_MODE,
        attribute_name="light_mode",
        type=LightMode,
        access=foundation.ZCLAttributeAccess.Read
        | foundation.ZCLAttributeAccess.Write
        | foundation.ZCLAttributeAccess.Report,
    )
    .tuya_dp_multi(
        dp_id=DP_MODE,
        attribute_mapping=[
            DPToAttributeMapping(
                TuyaMCUCluster.ep_attribute,
                "light_mode",
                converter=lambda v: LightMode(int(v)),
            ),
            DPToAttributeMapping(
                Color.ep_attribute,
                Color.AttributeDefs.color_mode.name,
                converter=dp2_to_color_mode,
            ),
        ],
        dp_converter=lambda mode, _color_mode=None: LightMode(int(mode)),
    )
    .tuya_dp(
        dp_id=DP_WHITE_BRIGHTNESS,
        ep_attribute=LevelControl.ep_attribute,
        attribute_name=LevelControl.AttributeDefs.current_level.name,
        converter=to_level,
    )
    .tuya_dp(
        dp_id=DP_COLOR_TEMP,
        ep_attribute=Color.ep_attribute,
        attribute_name=Color.AttributeDefs.color_temperature.name,
        converter=dp4_to_mireds,
    )
    .tuya_dp_multi(
        dp_id=DP_COLOR,
        attribute_mapping=[
            DPToAttributeMapping(
                Color.ep_attribute,
                Color.AttributeDefs.current_x.name,
                converter=dp5_to_x,
            ),
            DPToAttributeMapping(
                Color.ep_attribute,
                Color.AttributeDefs.current_y.name,
                converter=dp5_to_y,
            ),
            DPToAttributeMapping(
                LevelControl.ep_attribute,
                LevelControl.AttributeDefs.current_level.name,
                converter=dp5_to_level,
            ),
        ],
    )
    # DP6 carries effect, speed and palette together. Writing either the
    # effect or the speed rebuilds the whole string from the cached values.
    .tuya_attribute(
        dp_id=DP_EFFECT,
        attribute_name="string_effect",
        type=StringEffect,
        access=foundation.ZCLAttributeAccess.Read
        | foundation.ZCLAttributeAccess.Write
        | foundation.ZCLAttributeAccess.Report,
    )
    .tuya_attribute(
        dp_id=0xF6,  # not a device DP; local attribute id 0xEFF6
        attribute_name="effect_speed",
        type=t.uint8_t,
        access=foundation.ZCLAttributeAccess.Read
        | foundation.ZCLAttributeAccess.Write
        | foundation.ZCLAttributeAccess.Report,
    )
    .tuya_attribute(
        dp_id=0xF7,  # not a device DP; local attribute id 0xEFF7
        attribute_name="effect_palette",
        type=t.CharacterString,
        access=foundation.ZCLAttributeAccess.Read,
    )
    .tuya_dp_multi(
        dp_id=DP_EFFECT,
        attribute_mapping=[
            DPToAttributeMapping(
                TuyaMCUCluster.ep_attribute, "string_effect", converter=dp6_to_effect
            ),
            DPToAttributeMapping(
                TuyaMCUCluster.ep_attribute, "effect_speed", converter=dp6_to_speed
            ),
            DPToAttributeMapping(
                TuyaMCUCluster.ep_attribute, "effect_palette", converter=dp6_to_palette
            ),
        ],
        dp_converter=effect_to_dp6,
    )
    .enum(
        attribute_name="string_effect",
        enum_class=StringEffect,
        cluster_id=TUYA_CLUSTER_ID,
        entity_type=EntityType.STANDARD,
        translation_key="string_effect",
        fallback_name="Effect",
    )
    .number(
        attribute_name="effect_speed",
        cluster_id=TUYA_CLUSTER_ID,
        min_value=0,
        max_value=100,
        step=1,
        unit="%",
        mode="slider",
        entity_type=EntityType.STANDARD,
        translation_key="effect_speed",
        fallback_name="Effect speed",
    )
    .enum(
        attribute_name="light_mode",
        enum_class=LightMode,
        cluster_id=TUYA_CLUSTER_ID,
        entity_type=EntityType.STANDARD,
        translation_key="light_mode",
        fallback_name="Light mode",
    )
    .add_to_registry(replacement_cluster=MelineraTuyaCluster)
)
