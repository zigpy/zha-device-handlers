"""ZHA quirk for Lidl Melinera HG06467 smart LED string lights.

Device:
    manufacturer: _TZE200_s8gkrkxk
    model:        TS0601

Protocol (Tuya MCU cluster 0xEF00), as documented by zigbee-herdsman-converters
(src/lib/lidl.ts) and ptc/Melinera_HG06467:

    DP1 = power (bool). The physical button reports only this DP.
    DP2 = mode (enum): 0 white, 1 color, 2 effect
    DP3 = white brightness (value): 0..1000
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

Brightness, like in Zigbee2MQTT, never uses the device's own Level Control
cluster: in colour mode it is sent inside DP5, in white mode as DP3, and in
effect mode it is only kept for when the effect is left.

Exposed in Home Assistant, kept to as few controls as possible:
    - light: on/off, brightness, colour, and the 16 built-in effects in the
      light's own effect list. Picking white in the colour picker uses the
      string's white mode; picking a colour or "off" leaves the effect.
    - number "Effect speed": 0..100 %, applied at once in effect mode and
      otherwise kept for the next effect (as in Zigbee2MQTT)

Turning the light off from Home Assistant is a "soft off": the string is set
to white mode at zero brightness (zero brightness in colour mode does not
darken it) but the controller stays powered, because its power
supply hums when switched off. Turning on restores the colour, white or
effect. The physical button still switches the controller fully.
"""

from __future__ import annotations

import colorsys
from typing import Any

from zha.application.platforms.light import Light
from zha.application.platforms.light.const import EFFECT_OFF, LightEntityFeature
import zigpy.types as t
from zigpy.typing import UNDEFINED, UndefinedType
from zigpy.zcl import (
    AttributeReadEvent,
    AttributeReportedEvent,
    AttributeUpdatedEvent,
    AttributeWrittenEvent,
    foundation,
)
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
DP_COLOR = 5
DP_EFFECT = 6

DEFAULT_SPEED = 50  # percent
# Below this saturation (of 1000) a picked colour uses the white mode.
WHITE_SATURATION = 30
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


def current_hs(endpoint) -> tuple[float, float]:
    """Hue/saturation of the last colour, from the cached xy."""
    color = endpoint.light_color
    return xy_to_hs(
        (color.get(Color.AttributeDefs.current_x.name) or 0) / 65535,
        (color.get(Color.AttributeDefs.current_y.name) or 0) / 65535,
    )


class MelineraTuyaCluster(TuyaMCUCluster):
    """Tuya MCU cluster handling the mode-dependent datapoints."""

    async def send_dps(self, *datapoints: tuple[int, Any]) -> None:
        """Send datapoints to the string, in order."""
        for dp, value in datapoints:
            await self.command(
                self.mcu_write_command,
                TuyaCommand(
                    status=0,
                    tsn=self.endpoint.device.application.get_sequence(),
                    datapoints=[TuyaDatapointData(dp, value)],
                ),
                expect_reply=False,
            )

    def _dp_2_attr_update(self, datapoint: TuyaDatapointData) -> None:
        """Ignore brightness/colour echoes of another mode or of a soft off."""
        if self.get("soft_off") and datapoint.dp in (DP_WHITE_BRIGHTNESS, DP_COLOR):
            return
        mode = self.get("light_mode")
        if datapoint.dp == DP_WHITE_BRIGHTNESS and mode not in (None, LightMode.White):
            return
        if datapoint.dp == DP_COLOR and mode not in (None, LightMode.Color):
            return
        super()._dp_2_attr_update(datapoint)

    async def soft_off(self) -> None:
        """Darken the LEDs but keep the controller powered (it hums when off)."""
        mode = self.get("light_mode")
        if not self.get("soft_off"):
            self.update_attribute(
                "resume_mode", LightMode.White if mode is None else mode
            )
        self.update_attribute("soft_off", True)
        # Zero brightness darkens the string only in white mode (in colour
        # mode the LEDs stay lit), so go dark through white. DP3 is sent
        # before and after the mode so that no white flash is seen.
        await self.send_dps(
            (DP_WHITE_BRIGHTNESS, 0),
            (DP_MODE, LightMode.White),
            (DP_WHITE_BRIGHTNESS, 0),
        )
        self.update_attribute("light_mode", LightMode.White)

    async def resume(self) -> None:
        """Restore the mode, colour, brightness or effect from before soft off."""
        self.update_attribute("soft_off", False)
        mode = self.get("resume_mode")
        level = level_to_1000(
            self.endpoint.level.get(LevelControl.AttributeDefs.current_level.name)
        )
        if mode == LightMode.Effect:
            await self.send_dps(
                (DP_MODE, LightMode.Effect),
                (
                    DP_EFFECT,
                    effect_to_dp6(
                        self.get("string_effect"),
                        self.get("effect_speed"),
                        self.get("effect_palette"),
                    ),
                ),
            )
        elif mode == LightMode.Color:
            hue, sat = current_hs(self.endpoint)
            await self.send_dps(
                (DP_MODE, LightMode.Color), (DP_COLOR, encode_hsb(hue, sat, level))
            )
        else:
            mode = LightMode.White
            await self.send_dps(
                (DP_MODE, LightMode.White), (DP_WHITE_BRIGHTNESS, level)
            )
        self.update_attribute("light_mode", mode)

    async def write_attributes(
        self,
        attributes: dict[str | int | foundation.ZCLAttributeDef, Any],
        manufacturer: int | UndefinedType | None = UNDEFINED,
        **kwargs,
    ) -> list[list[foundation.WriteAttributesStatusRecord]]:
        """Send effect changes with the effect mode; keep speed outside it."""
        remaining: dict[str | int | foundation.ZCLAttributeDef, Any] = {}
        effect_changes: dict[str, Any] = {}
        for key, value in attributes.items():
            attr = self.find_attribute(key)
            if attr.name in ("string_effect", "effect_speed"):
                effect_changes[attr.name] = attr.type(value)
            else:
                remaining[key] = value

        if effect_changes:
            for name, value in effect_changes.items():
                self.update_attribute(name, value)
            # A speed change alone outside effect mode is only remembered.
            if (
                "string_effect" in effect_changes
                or self.get("light_mode") == LightMode.Effect
            ):
                await self.send_dps(
                    (DP_MODE, LightMode.Effect),
                    (
                        DP_EFFECT,
                        effect_to_dp6(
                            self.get("string_effect"),
                            self.get("effect_speed"),
                            self.get("effect_palette"),
                        ),
                    ),
                )
                self.update_attribute("light_mode", LightMode.Effect)

        if remaining:
            return await super().write_attributes(
                remaining, manufacturer=manufacturer, **kwargs
            )
        return [[foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)]]


def _success(command_id: int) -> foundation.DefaultResponse:
    return foundation.GENERAL_COMMANDS[
        foundation.GeneralCommand.Default_Response
    ].schema(command_id=command_id, status=foundation.Status.SUCCESS)


class MelineraLevelCluster(CustomCluster, LevelControl):
    """Send brightness as the datapoint of the active mode."""

    async def read_attributes(self, attributes, **kwargs):
        """Serve reads from the cache; the device's cluster lacks the Tuya state."""
        kwargs.pop("allow_cache", None)
        kwargs.pop("only_cache", None)
        return await super().read_attributes(
            attributes, allow_cache=True, only_cache=True, **kwargs
        )

    async def command(self, command_id, *args, **kwargs):
        """Handle move to level by mode, as Zigbee2MQTT does."""
        if command_id not in (
            LevelControl.ServerCommandDefs.move_to_level.id,
            LevelControl.ServerCommandDefs.move_to_level_with_on_off.id,
        ):
            return await super().command(command_id, *args, **kwargs)

        level = int(kwargs.get("level", args[0] if args else 254))
        on_off = (
            command_id == LevelControl.ServerCommandDefs.move_to_level_with_on_off.id
        )
        if on_off and level == 0:
            await self.endpoint.on_off.off()
            return _success(command_id)

        tuya: MelineraTuyaCluster = self.endpoint.tuya_manufacturer
        mode = tuya.get("light_mode")
        if mode == LightMode.Color:
            hue, sat = current_hs(self.endpoint)
            await tuya.send_dps((DP_COLOR, encode_hsb(hue, sat, level_to_1000(level))))
        elif mode != LightMode.Effect:
            # White mode (or unknown): DP3. In effect mode it is only kept.
            await tuya.send_dps((DP_WHITE_BRIGHTNESS, level_to_1000(level)))
        self.update_attribute(LevelControl.AttributeDefs.current_level.name, level)

        if on_off and not self.endpoint.on_off.get(OnOff.AttributeDefs.on_off.name):
            await self.endpoint.on_off.on()
        return _success(command_id)


class MelineraColorCluster(CustomCluster, Color):
    """Translate ZCL xy commands into Tuya datapoints."""

    _CONSTANT_ATTRIBUTES = {
        Color.AttributeDefs.color_capabilities.id: (
            Color.ColorCapabilities.XY_attributes
        ),
        Color.AttributeDefs.color_mode.id: Color.ColorMode.X_and_Y,
        # The string has no colour temperature; hide any cached value.
        Color.AttributeDefs.color_temperature.id: None,
    }

    async def read_attributes(self, attributes, **kwargs):
        """Serve reads from the cache; the device's cluster lacks the Tuya state."""
        kwargs.pop("allow_cache", None)
        kwargs.pop("only_cache", None)
        return await super().read_attributes(
            attributes, allow_cache=True, only_cache=True, **kwargs
        )

    async def command(self, command_id, *args, **kwargs):
        """Handle xy colour commands via Tuya datapoints."""
        if command_id != Color.ServerCommandDefs.move_to_color.id:
            return await super().command(command_id, *args, **kwargs)

        x = int(kwargs.get("color_x", args[0] if args else 0))
        y = int(kwargs.get("color_y", args[1] if len(args) > 1 else 0))
        hue, sat = xy_to_hs(x / 65535, y / 65535)
        level = self.endpoint.level.get(LevelControl.AttributeDefs.current_level.name)

        tuya: MelineraTuyaCluster = self.endpoint.tuya_manufacturer
        if sat < WHITE_SATURATION:
            await tuya.send_dps(
                (DP_MODE, LightMode.White),
                (DP_WHITE_BRIGHTNESS, level_to_1000(level)),
            )
            tuya.update_attribute("light_mode", LightMode.White)
        else:
            await tuya.send_dps(
                (DP_MODE, LightMode.Color),
                (DP_COLOR, encode_hsb(hue, sat, level_to_1000(level))),
            )
            tuya.update_attribute("light_mode", LightMode.Color)
        self.update_attribute(Color.AttributeDefs.current_x.name, x)
        self.update_attribute(Color.AttributeDefs.current_y.name, y)
        return _success(command_id)


EFFECT_NAMES: dict[StringEffect, str] = {
    effect: effect.name.replace("_", " ") for effect in StringEffect
}


class MelineraLight(Light):
    """Light with the string's built-in effects in its own effect list."""

    @property
    def _tuya(self) -> MelineraTuyaCluster | None:
        on_off = getattr(self, "_on_off_cluster", None)
        return getattr(on_off.endpoint, "tuya_manufacturer", None) if on_off else None

    def _current_effect(self) -> str:
        tuya = self._tuya
        if tuya is None or tuya.get("light_mode") != LightMode.Effect:
            return EFFECT_OFF
        effect = tuya.get("string_effect")
        return (
            EFFECT_NAMES.get(StringEffect(effect), EFFECT_OFF)
            if effect is not None
            else EFFECT_OFF
        )

    @property
    def _powered(self) -> bool:
        """Whether the controller itself is on (also while soft off)."""
        return bool(getattr(self, "_state", False))

    @property
    def is_on(self) -> bool:
        """Return false while the string is soft off."""
        tuya = self._tuya
        return super().is_on and not (tuya is not None and tuya.get("soft_off"))

    def handle_attribute_updated(self, event) -> None:
        """Resume when the physical button powers a soft-off string back on."""
        was_on = self._powered
        super().handle_attribute_updated(event)
        tuya = self._tuya
        if tuya is not None and tuya.get("soft_off") and self._powered and not was_on:
            self._device.gateway.async_create_task(self._resume_from_button())

    async def _resume_from_button(self) -> None:
        tuya = self._tuya
        assert tuya is not None
        await tuya.resume()
        self.maybe_emit_state_changed_event()

    async def async_turn_off(self, *, transition: float | None = None) -> None:
        """Turn off without powering the controller down, which makes it hum."""
        tuya = self._tuya
        assert tuya is not None
        if self._powered:
            await tuya.soft_off()
        self._effect = EFFECT_OFF
        self.maybe_emit_state_changed_event()

    def recompute_capabilities(self) -> None:
        """Offer the built-in effects instead of colour loop."""
        super().recompute_capabilities()
        self._supported_features |= LightEntityFeature.EFFECT
        self._effect_list = [EFFECT_OFF, *EFFECT_NAMES.values()]
        self._effect = self._current_effect()

    def on_add(self) -> None:
        """Follow mode and effect changes, including the physical button."""
        super().on_add()
        tuya = self._tuya
        assert tuya is not None
        for event_type in (
            AttributeReadEvent,
            AttributeReportedEvent,
            AttributeUpdatedEvent,
            AttributeWrittenEvent,
        ):
            self._on_remove_callbacks.append(
                tuya.on_event(event_type.event_type, self._handle_tuya_update)
            )

    def _handle_tuya_update(self, event) -> None:
        if event.attribute_name not in ("light_mode", "string_effect"):
            return
        effect = self._current_effect()
        if effect != self._effect:
            self._effect = effect
            self.maybe_emit_state_changed_event()

    async def async_turn_on(self, *, effect: str | None = None, **kwargs) -> None:
        """Turn on, optionally starting or leaving a built-in effect."""
        tuya = self._tuya
        assert tuya is not None
        if tuya.get("soft_off"):
            if not self._powered:
                await self._on_off_cluster.on()
                self._state = True
            await tuya.resume()
            self._effect = self._current_effect()
        in_effect = tuya.get("light_mode") == LightMode.Effect

        chosen = next((e for e, n in EFFECT_NAMES.items() if n == effect), None)
        if chosen is not None:
            if not self.is_on:
                await self._on_off_cluster.on()
                self._state = True
            await tuya.write_attributes({"string_effect": chosen})
            self._effect = effect
            if all(value is None for value in kwargs.values()):
                self.maybe_emit_state_changed_event()
                return
        elif (
            effect == EFFECT_OFF
            and in_effect
            and kwargs.get("xy_color") is None
            and self._color_cluster is not None
        ):
            # Leave the effect for the last colour.
            x, y = self._xy_color or (0.0, 0.0)
            await self._color_cluster.move_to_color(
                color_x=round(x * 65535), color_y=round(y * 65535), transition_time=0
            )
            self._effect = EFFECT_OFF

        await super().async_turn_on(**kwargs)


(
    TuyaQuirkBuilder("_TZE200_s8gkrkxk", "TS0601")
    .replaces(MelineraColorCluster)
    .replaces(MelineraLevelCluster)
    .replaces_entity(Light, MelineraLight, endpoint_id=1, cluster_id=OnOff.cluster_id)
    # Physical button: the string reports power only through DP1.
    .tuya_dp(
        dp_id=DP_POWER,
        ep_attribute=OnOff.ep_attribute,
        attribute_name=OnOff.AttributeDefs.on_off.name,
        converter=lambda v: t.Bool(bool(v)),
    )
    .tuya_dp_attribute(
        dp_id=DP_MODE,
        attribute_name="light_mode",
        type=LightMode,
        access=foundation.ZCLAttributeAccess.Read
        | foundation.ZCLAttributeAccess.Write
        | foundation.ZCLAttributeAccess.Report,
        converter=lambda v: LightMode(int(v)),
    )
    .tuya_dp(
        dp_id=DP_WHITE_BRIGHTNESS,
        ep_attribute=LevelControl.ep_attribute,
        attribute_name=LevelControl.AttributeDefs.current_level.name,
        converter=to_level,
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
    # DP6 carries effect, speed and palette together; writes are built in
    # MelineraTuyaCluster.write_attributes.
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
    .tuya_attribute(
        dp_id=0xF8,  # not a device DP; local attribute id 0xEFF8
        attribute_name="soft_off",
        type=t.Bool,
        access=foundation.ZCLAttributeAccess.Read,
    )
    .tuya_attribute(
        dp_id=0xF9,  # not a device DP; local attribute id 0xEFF9
        attribute_name="resume_mode",
        type=LightMode,
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
    .add_to_registry(replacement_cluster=MelineraTuyaCluster)
)
