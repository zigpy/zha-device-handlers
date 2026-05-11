"""Philips Hue native control via cluster 0xFC03 — v3 device-level quirk."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Final

from zha.application import Platform
from zha.application.platforms.light import Light
from zha.zigbee.device import Device, DeviceMatch, Replace, register_device
from zigpy.quirks import CustomCluster
import zigpy.types as t
from zigpy.zcl import ClusterType
from zigpy.zcl.clusters.general import LevelControl, OnOff
from zigpy.zcl.clusters.lighting import Color
from zigpy.zcl.foundation import BaseCommandDefs, ZCLCommandDef

from zhaquirks.philips.bifrost import (
    HUE_FC03_CLUSTER_ID,
    HUE_NATIVE_COMMAND_ID,
    GradientColors,
    GradientStyle,
    HueEffect,
    HueFrame,
    decode,
    encode,
)

_LOGGER = logging.getLogger(__name__)

PHILIPS = "Philips"
SIGNIFY = "Signify Netherlands B.V."

EFFECT_NAME_TO_HUE: dict[str, HueEffect] = {
    "none": HueEffect.NO_EFFECT,
    "candle": HueEffect.CANDLE,
    "fireplace": HueEffect.FIREPLACE,
    "prism": HueEffect.PRISM,
    "sunrise": HueEffect.SUNRISE,
    "sunset": HueEffect.SUNSET,
    "sparkle": HueEffect.SPARKLE,
    "opal": HueEffect.OPAL,
    "glisten": HueEffect.GLISTEN,
    "underwater": HueEffect.UNDERWATER,
    "cosmos": HueEffect.COSMOS,
    "sunbeam": HueEffect.SUNBEAM,
    "enchant": HueEffect.ENCHANT,
}
HUE_TO_EFFECT_NAME: dict[HueEffect, str] = {v: k for k, v in EFFECT_NAME_TO_HUE.items()}

_POST_EFFECT_REFRESH_DELAY = 1.0


class HueLightCluster(CustomCluster):
    """Philips Hue manufacturer cluster carrying the Bifrost native-control command."""

    cluster_id: Final[t.uint16_t] = HUE_FC03_CLUSTER_ID
    ep_attribute: Final[str] = "philips_hue_light"

    class ServerCommandDefs(BaseCommandDefs):
        """Server commands."""

        hue_native: Final = ZCLCommandDef(
            id=HUE_NATIVE_COMMAND_ID,
            schema={"data": t.SerializableBytes},
            is_manufacturer_specific=True,
        )


class HueNativeLight(Light):
    """Light driven by atomic Bifrost frames on cluster 0xFC03."""

    _attr_translation_key = "hue_native_light"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._fc03_handler = self.cluster_handlers[HueLightCluster.ep_attribute]

    @property
    def effect_list(self) -> list[str] | None:
        return list(EFFECT_NAME_TO_HUE)

    def on_add(self) -> None:
        super().on_add()
        # Hue lights publish state via cluster commands on 0xFC03; subscribe.
        self._fc03_handler.cluster.add_listener(self)

    def cluster_command(self, tsn: int, command_id: int, args: list[Any]) -> None:
        """Handle a server-issued cluster command on 0xFC03."""
        if command_id != HUE_NATIVE_COMMAND_ID:
            return
        payload: t.SerializableBytes = args[0]
        try:
            frame = decode(bytes(payload.serialize()))
        except ValueError:
            _LOGGER.exception("Failed to decode Hue native frame: %s", payload)
            return
        self._apply_frame(frame)

    def _apply_frame(self, frame: HueFrame) -> None:
        if frame.on_off is not None:
            self._state = frame.on_off
        if frame.brightness is not None:
            self._brightness = frame.brightness
        if frame.color_xy is not None:
            self._xy_color = frame.color_xy
        if frame.color_mirek is not None:
            self._color_temp = frame.color_mirek
        if frame.effect_type is not None:
            self._effect = HUE_TO_EFFECT_NAME.get(frame.effect_type, "none")
        self.maybe_emit_state_changed_event()

    async def _async_turn_on_impl(
        self,
        *,
        transition: float | None,
        brightness: int | None,
        effect: str | None,
        flash: Any,
        color_temp: int | None,
        xy_color: tuple[float, float] | None,
        duration: float,
        **_unused: Any,
    ) -> None:
        del flash, _unused  # Flash uses the Identify cluster, not Bifrost.
        frame = HueFrame(
            on_off=True,
            brightness=_clamp_brightness(brightness),
            color_mirek=color_temp,
            color_xy=xy_color,
            fade_speed=_seconds_to_fade_speed(transition or duration),
            effect_type=EFFECT_NAME_TO_HUE.get(effect) if effect else None,
        )
        await self._send_frame(frame)
        if effect and EFFECT_NAME_TO_HUE.get(effect) not in (None, HueEffect.NO_EFFECT):
            asyncio.get_running_loop().call_later(
                _POST_EFFECT_REFRESH_DELAY,
                lambda: asyncio.create_task(self._refresh_state()),
            )

    async def async_turn_off(self, *, transition: float | None = None) -> None:
        await self._send_frame(
            HueFrame(
                on_off=False,
                fade_speed=_seconds_to_fade_speed(transition),
            )
        )

    async def _send_frame(self, frame: HueFrame) -> None:
        payload = encode(frame)
        _LOGGER.debug("Hue native frame: %s", payload.hex())
        await self._fc03_handler.cluster.hue_native(t.SerializableBytes(payload))

    async def _refresh_state(self) -> None:
        # OnOff/Level/Color report standard attributes; trigger a re-poll.
        await self._on_off_cluster_handler.cluster.read_attributes(
            ["on_off"], allow_cache=False
        )


class HueNativeGradientLight(HueNativeLight):
    """Hue light with multi-color gradient support (e.g. LCX004)."""

    _attr_translation_key = "hue_native_gradient_light"

    async def async_set_gradient(
        self,
        colors: list[tuple[float, float]],
        *,
        style: GradientStyle = GradientStyle.LINEAR,
        scale: float = 7.0,
        offset: float = 0.0,
    ) -> None:
        await self._send_frame(
            HueFrame(
                on_off=True,
                gradient_colors=GradientColors(style=style, colors=tuple(colors)),
                gradient_params=(scale, offset),
            )
        )


def _clamp_brightness(brightness: int | None) -> int | None:
    if brightness is None:
        return None
    return max(1, min(254, brightness))


def _seconds_to_fade_speed(seconds: float | None) -> int | None:
    if seconds is None:
        return None
    return max(0, min(0xFFFF, round(seconds * 10)))


@register_device
class HueLcx004(Device):
    """Hue Play gradient lightstrip (LCX004) — Bifrost-native control."""

    _device_match = DeviceMatch(
        manufacturers=frozenset({PHILIPS, SIGNIFY}),
        models=frozenset({"LCX004"}),
    )
    _operations = (
        Replace(
            endpoint_id=11,
            cluster_id=HUE_FC03_CLUSTER_ID,
            cluster_type=ClusterType.Server,
            replacement=HueLightCluster,
        ),
    )

    def discover_entities(self):
        for entity in super().discover_entities():
            if entity.PLATFORM == Platform.LIGHT:
                continue
            yield entity

        for ep_id, endpoint in self.endpoints.items():
            if ep_id == 0:
                continue

            handlers = endpoint.all_cluster_handlers
            on_off = handlers.get(f"{ep_id}:0x{OnOff.cluster_id:04x}")
            fc03 = handlers.get(f"{ep_id}:0x{HUE_FC03_CLUSTER_ID:04x}")
            if on_off is None or fc03 is None:
                continue

            cluster_handlers = [on_off, fc03]
            for opt_id in (LevelControl.cluster_id, Color.cluster_id):
                ch = handlers.get(f"{ep_id}:0x{opt_id:04x}")
                if ch is not None:
                    cluster_handlers.append(ch)

            yield HueNativeGradientLight(
                cluster_handlers=cluster_handlers,
                endpoint=endpoint,
                device=self,
            )
