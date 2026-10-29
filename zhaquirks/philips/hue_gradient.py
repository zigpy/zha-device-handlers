"""Native Hue effects and gradient scenes for Philips Hue gradient lights.

Hue effects and gradients are not part of the ZCL: they are sent as one frame with
the `multicolor` command of the manufacturer-specific cluster 0xFC03, which also
reports the current light state in the same format. A frame is a 16-bit
little-endian flag bitmap followed by the flagged fields in a fixed wire order: on/off,
brightness, mirek, xy, fade speed, effect type, gradient colors, effect speed and
gradient params.

References:
- https://github.com/chrivers/bifrost/blob/master/doc/hue-zigbee-format.md
- zigbee-herdsman-converters `src/lib/philips.ts` (MIT), the source of the effect IDs
  and the gradient scene frames below

"""

from __future__ import annotations

from typing import Any, Final

from zha.application.helpers import safe_read
from zha.application.platforms import ZclPlatformEntity
from zha.application.platforms.light import HueLight
from zha.application.platforms.light.const import (
    EFFECT_OFF,
    ColorMode,
    FlashMode,
    LightEntityFeature,
)
from zha.application.platforms.select import BaseSelectEntity, EnumSelectState
import zigpy.types as t

from zhaquirks.philips import PhilipsHueLightCluster

FLAG_ON_OFF: Final = 0x0001
FLAG_BRIGHTNESS: Final = 0x0002
FLAG_COLOR_MIREK: Final = 0x0004
FLAG_COLOR_XY: Final = 0x0008
FLAG_FADE_SPEED: Final = 0x0010
FLAG_EFFECT_TYPE: Final = 0x0020
FLAG_GRADIENT_COLORS: Final = 0x0100

# Fields preceding the effect type in the wire format, with their sizes in bytes
_FIELDS_BEFORE_EFFECT: Final = (
    (FLAG_ON_OFF, 1),
    (FLAG_BRIGHTNESS, 1),
    (FLAG_COLOR_MIREK, 2),
    (FLAG_COLOR_XY, 4),
    (FLAG_FADE_SPEED, 2),
)

# "prism" is the Hue variant of a color loop; the ZCL "colorloop" stays available
HUE_EFFECTS: Final[dict[str, int]] = {
    "candle": 0x01,
    "fireplace": 0x02,
    "prism": 0x03,
    "sunrise": 0x09,
    "sparkle": 0x0A,
    "opal": 0x0B,
    "glisten": 0x0C,
    "sunset": 0x0D,
    "underwater": 0x0E,
    "cosmos": 0x0F,
    "sunbeam": 0x10,
    "enchant": 0x11,
}
HUE_EFFECT_NAMES: Final[dict[int, str]] = {v: k for k, v in HUE_EFFECTS.items()}

# Stops the running Hue effect, keeping the current color and brightness
STOP_EFFECT_FRAME: Final = bytes([FLAG_EFFECT_TYPE, 0x00, 0x00])

GRADIENT_OFF: Final = "off"

# Frames with fade speed, gradient colors and gradient params
GRADIENT_SCENES: Final[dict[str, str]] = {
    "blossom": "50010400135000000039d553d2955ba5287a9f697e25fb802800",
    "crocus": "50010400135000000050389322f97f2b597343764cc664282800",
    "precious": "5001040013500000007fa8838bb9789a786d7577499a773f2800",
    "narcissa": "500104001350000000b0498a5c0a888fea89eb0b7ee15c742800",
    "beginnings": "500104001350000000b3474def153e2ad42e98232c7483292800",
    "first light": "500104001350000000b28b7900e959d3f648a614389723362800",
    "horizon": "500104001350000000488b7d6cbb750c6642f1133cc4033c2800",
    "valley dawn": "500104001350000000c1aa7de03a7a8ce861c7c4410d94412800",
    "sunflare": "500104001350000000d0aa7d787a7daf197590154d6c14472800",
    "emerald flutter": "5001040013500000006a933977e34bb0d35e916468f246792800",
    "memento": "500104001350000000f87318a3e31962331ec3532cceea892800",
    "resplendent": "500104001350000000278b6d257a58efe84204273a35f5252800",
    "scarlet dream": "500104001350000000b02c654e4c5b45ab51fb0950d6c84d2800",
    "lovebirds": "50010400135000000053ab84ea1a7e35fb7c098c73994c772800",
    "smitten": "500104001350000000fe7b70a74b6aa42b65811b60550a592800",
    "glitz and glam": "500104001350000000cc193cb9b845bad9521d1c77bf6c712800",
    "promise": "500104001350000000258b606eca6b28d6382db445df26812800",
    "ruby romance": "5001040013500000000edb63cbcb6bac0c670b2d58204e572800",
    "city of love": "50010400135000000055830e5cf31b6aa339d2ec70908b802800",
    "honolulu": "500104001350000000dbfd59866c6378ec6c45cc765c0a822800",
    "savanna sunset": "50010400135000000005ae65c38c6c6b4b7573ca820fc9832800",
    "golden pond": "5001040013500000007e4a88cc4a8605db8728ec7b666c792800",
    "ruby glow": "50010400135000000095bb53ac2a56eb99591e095c54985e2800",
    "tropical twilight": "500104001350000000408523a0b636e777524c0a71a76c6e2800",
    "miami": "50010400135000000022ec61e6d94902d83766c3305a43182800",
    "cancun": "500104001350000000a7eb54673d55944e6265fd6e26bb842800",
    "rio": "500104001350000000a26526088c51a74b58ea6b7137ba892800",
    "chinatown": "500104001350000000b33e5b408e59d90d5b4c6c6360ac792800",
    "ibiza": "500104001350000000014d6d708c73827b7b6c7a8887f98a2800",
    "osaka": "500104001350000000d649510b5c4deb7c5d8b6d6d2b9b802800",
    "tokyo": "500104001350000000d1c311665331d3451fd59c4e394c7b2800",
    "motown": "50010400135000000055730e5db3156623306c533d7a235c2800",
    "fairfax": "50010400135000000072d34a3664477d7a61581d5fc08e5b2800",
    "galaxy": "500104001350000000a6cb638b2a4f8cfa549bb9549ff73a2800",
    "starlight": "5001040013500000008d897134a9653ec854d2963ed1d4282800",
    "blood moon": "500104001350000000202a6987c8599ee647ec632779c3142800",
    "arctic aurora": "50010400135000000082548922057511046571c32d5b93192800",
    "moonlight": "50010400135000000055730e5e9320c1832e96243ebec7652800",
    "nebula": "50010400135000000026c852e106460d653ee745342964142800",
    "sundown": "500104001350000000f37c68157c6d8efa755ac5512e24332800",
    "blue lagoon": "50010400135000000088c3623975699ea672a0c8831ada6d2800",
    "palm beach": "5001040013500000005ec4679ba56077f85a80ea64639c6a2800",
    "lake placid": "5001040013500000002eab69239a692d996552c54c39743a2800",
    "mountain breeze": "500104001350000000df843d2355419195465a98674ca97b2800",
    "lake mist": "500104001350000000e3286f39b96859f86266e54ded943f2800",
    "ocean dawn": "5001040013500000005cf9779da97105b96b07485e32564a2800",
    "frosty dawn": "5001040013500000006d6883bca87e3029758ec9722d6a722800",
    "sunday morning": "5001040013500000002c586dc6f87345997c63f983f777892800",
    "emerald isle": "500104001350000000e535628dc57ed2667d8b687d1e2a812800",
    "spring blossom": "500104001350000000a8b75fd0c75826b851a7094d305b652800",
    "midsummer sun": "500104001350000000002984799984dd29848eba836c0b7f2800",
    "autumn gold": "500104001350000000435a7817aa7ba3f979a8a981f3c9852800",
    "spring lake": "5001040013500000004a976d3347736e677561b77a4b07812800",
    "winter mountain": "5001040013500000002c555c68c55d7c555ef165606136622800",
    "midwinter": "500104001350000000bda5532c554dbd254cd5a4428d94392800",
    "amber bloom": "500104001350000000739d67f2bc7372ec78a0ab78be8a6f2800",
    "lily": "5001040013500000009cfc76c5ab793d4a6a1a9b586b9c522800",
    "painted sky": "500104001350000000d1c424c3d63783384c3f7a6a83bd6d2800",
    "winter beauty": "500104001350000000e2335ea7b4942467952db986a7ab7b2800",
    "orange fields": "500104001350000000409c69694c79eafa88498a8fb867aa2800",
    "forest adventure": "50010400135000000023999bbd76b363d4b674d3415fb3222800",
    "blue planet": "50010400135000000037a7a3a403b489737b2b746e6873362800",
    "soho": "500104001350000000c52c4e220b6eed8a53d404192b04782800",
    "vapor wave": "500104001350000000e1c32401251acb183ac31b8051ea842800",
    "magneto": "50010400135000000077b3286d9340b9e3662d99943c9b852800",
    "tyrell": "500104001350000000ef4419a898370ea84698353574434e2800",
    "disturbia": "50010400135000000084f371a4845e6998388c3b4f57ce582800",
    "hal": "50010400135000000075f351a6244cf6dc5d480c658cda862800",
    "golden star": "5001040013500000007a4a8702eb8372ac7892cd61d51e5c2800",
    "under the tree": "5001040013500000001de498b9a3cc0c9b8563bb6cc1ae5d2800",
    "silent night": "5001040013500000009e296a245a6f660a75086b70953b6e2800",
    "rosy sparkle": "500104001350000000810967c63a6cb2aa5ea7094eddd73c2800",
    "festive fun": "5001040013500000005a9318de53123e9414fdcc67839d612800",
    "colour burst": "500104001350000000f2731ff0c6266a6c64246e57d4f98f2800",
    "crystalline": "5001040013500000006ea96a92a85e58074e18543d9cf3332800",
}


def effect_frame(effect_id: int, brightness: int | None = None) -> bytes:
    """Build a frame that turns the light on and starts a Hue effect."""
    flags = FLAG_ON_OFF | FLAG_EFFECT_TYPE
    body = bytearray([0x01])
    if brightness is not None:
        flags |= FLAG_BRIGHTNESS
        body.append(max(1, min(254, brightness)))
    body.append(effect_id)
    return flags.to_bytes(2, "little") + bytes(body)


def scene_frame(scene: str) -> bytes:
    """Build a gradient scene frame that also turns the light on and stops effects.

    In wire order, on/off follows the flags and the effect type follows the fade speed.
    """
    frame = bytes.fromhex(GRADIENT_SCENES[scene])
    flags = int.from_bytes(frame[:2], "little") | FLAG_ON_OFF | FLAG_EFFECT_TYPE
    return flags.to_bytes(2, "little") + b"\x01" + frame[2:4] + b"\x00" + frame[4:]


def decode_flags(frame: bytes) -> int | None:
    """Return the flag bitmap of a state frame."""
    if len(frame) < 2:
        return None
    return int.from_bytes(frame[:2], "little")


def decode_effect(frame: bytes) -> int | None:
    """Return the active effect ID from a state frame (0 is no effect)."""
    flags = decode_flags(frame)
    if flags is None:
        return None
    if not flags & FLAG_EFFECT_TYPE:
        return 0
    position = 2
    for flag, size in _FIELDS_BEFORE_EFFECT:
        if flags & flag:
            position += size
    return frame[position] if position < len(frame) else None


def find_endpoint_entity[T: ZclPlatformEntity](
    entity: ZclPlatformEntity, entity_cls: type[T]
) -> T | None:
    """Return the entity of `entity_cls` on the same endpoint as `entity`."""
    for other in entity.device.platform_entities.values():
        if isinstance(other, entity_cls) and other.endpoint.id == entity.endpoint.id:
            return other
    return None


class HueEffectsLight(HueLight):
    """Hue light that adds the native Hue effects to the effect list."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize the light."""
        super().__init__(*args, **kwargs)
        self._hue_cluster = self.endpoint.zigpy_endpoint.in_clusters[
            PhilipsHueLightCluster.cluster_id
        ]

    def recompute_capabilities(self) -> None:
        """Recompute capabilities."""
        super().recompute_capabilities()
        self._supported_features |= LightEntityFeature.EFFECT
        self._effect_list = [*(self.effect_list or [EFFECT_OFF]), *HUE_EFFECTS]

    async def _send_hue_frame(self, frame: bytes) -> None:
        self.debug("sending Hue frame: %s", frame.hex())
        await self._hue_cluster.multicolor(data=t.SerializableBytes(frame))

    def _gradient_ended(self) -> None:
        """Tell the gradient scene select that the gradient was replaced."""
        select = find_endpoint_entity(self, HueGradientSceneSelect)
        if select is not None:
            select.set_gradient_off()

    async def async_turn_on(
        self,
        *,
        transition: float | None = None,
        brightness: int | None = None,
        effect: str | None = None,
        flash: FlashMode | None = None,
        color_temp: int | None = None,
        xy_color: tuple[float, float] | None = None,
    ) -> None:
        """Turn the entity on, starting or stopping a Hue effect if needed."""
        if effect in HUE_EFFECTS:
            # Set the base color first: the effect builds on the current color
            if color_temp is not None or xy_color is not None or flash is not None:
                await super().async_turn_on(
                    transition=transition,
                    color_temp=color_temp,
                    xy_color=xy_color,
                    flash=flash,
                )
            await self._send_hue_frame(effect_frame(HUE_EFFECTS[effect], brightness))
            self._state = True
            if brightness is not None:
                self._brightness = brightness
            self._effect = effect
            self.maybe_emit_state_changed_event()
            self._gradient_ended()
            return

        # A single color or another effect replaces the gradient
        if (
            color_temp is not None
            or xy_color is not None
            or effect not in (None, EFFECT_OFF)
        ):
            self._gradient_ended()

        # Any other effect or a new color ends the running Hue effect
        if self._effect in HUE_EFFECTS and (
            effect is not None or color_temp is not None or xy_color is not None
        ):
            await self._send_hue_frame(STOP_EFFECT_FRAME)
            self._effect = EFFECT_OFF

        await super().async_turn_on(
            transition=transition,
            brightness=brightness,
            effect=effect,
            flash=flash,
            color_temp=color_temp,
            xy_color=xy_color,
        )

    async def async_turn_off(self, *, transition: float | None = None) -> None:
        """Turn the entity off."""
        await super().async_turn_off(transition=transition)
        if self._effect in HUE_EFFECTS:
            self._effect = EFFECT_OFF
            self.maybe_emit_state_changed_event()

    async def async_update(self) -> None:
        """Poll the light, including the active Hue effect and gradient."""
        effect = self._effect
        await super().async_update()

        # The base light only knows the ZCL color loop and resets anything else
        if effect in HUE_EFFECTS:
            self._effect = effect

        if (
            self.is_transitioning
            or not self.device.gateway.config.allow_polling
            or not self.device.available
        ):
            return

        results = await safe_read(
            self._hue_cluster,
            [PhilipsHueLightCluster.AttributeDefs.state.name],
            allow_cache=False,
            only_cache=False,
        )
        frame = results.get(PhilipsHueLightCluster.AttributeDefs.state.name)
        frame = bytes(frame) if frame is not None else b""

        # Only trust a missing gradient while on: an off light may omit it
        flags = decode_flags(frame)
        if flags is not None and self._state and not flags & FLAG_GRADIENT_COLORS:
            self._gradient_ended()

        effect_id = decode_effect(frame)
        if effect_id is not None:
            if effect_id in HUE_EFFECT_NAMES:
                self._effect = HUE_EFFECT_NAMES[effect_id]
            elif self._effect in HUE_EFFECTS:
                self._effect = EFFECT_OFF

        if not self._state and self._effect in HUE_EFFECTS:
            self._effect = EFFECT_OFF
        self.maybe_emit_state_changed_event()


class HueGradientSceneSelect(BaseSelectEntity, ZclPlatformEntity):
    """Select entity that applies one of the Hue gradient scenes."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize the select entity."""
        self._attr_options = [GRADIENT_OFF, *GRADIENT_SCENES]
        self._current_option: str = GRADIENT_OFF
        super().__init__(*args, **kwargs)

    @property
    def state(self) -> EnumSelectState:
        """Return the state of the select."""
        return EnumSelectState(
            **super().state.__dict__,
            enum="HueGradientScene",
            options=self.options,
        )

    @property
    def current_option(self) -> str | None:
        """Return the active gradient scene, or off."""
        return self._current_option

    def set_gradient_off(self) -> None:
        """Mark the gradient as replaced by a single color or an effect."""
        if self._current_option != GRADIENT_OFF:
            self._current_option = GRADIENT_OFF
            self.maybe_emit_state_changed_event()

    async def async_select_option(self, option: str) -> None:
        """Apply a gradient scene, or return to a single color."""
        light = find_endpoint_entity(self, HueEffectsLight)

        if option == GRADIENT_OFF:
            # Re-applying the light's own color makes the whole light uniform
            if light is not None and light.is_on:
                state = light.state
                if state.color_mode == ColorMode.COLOR_TEMP and state.color_temp:
                    await light.async_turn_on(color_temp=state.color_temp)
                elif state.xy_color is not None:
                    await light.async_turn_on(xy_color=state.xy_color)
            self.set_gradient_off()
            return

        await self.cluster.multicolor(data=t.SerializableBytes(scene_frame(option)))
        self._current_option = option
        self.maybe_emit_state_changed_event()

        # The scene frame turns the light on and stops any running effect
        if light is not None:
            light._state = True
            light._effect = EFFECT_OFF
            light.maybe_emit_state_changed_event()

    def restore_external_state_attributes(self, *, state: str) -> None:
        """Restore the active gradient scene."""
        if state == GRADIENT_OFF or state in GRADIENT_SCENES:
            self._current_option = state
