"""GLEDOPTO GL-C-008P RGB+CCT LED controller.

The controller reports a fixed color temperature range, but the white channels
of the connected LED strip determine the real range. This quirk lets the user
enter the warmest and coldest temperature of the strip. Home Assistant then
works with that range, while commands and attribute values are mapped linearly
onto the native range of the controller.

The quirk also adds a configurable color loop time, which is used when the
color loop effect is started and is applied to a running color loop.
"""

from __future__ import annotations

import logging
from typing import Any, Final

from zha.application.platforms.light import Light
import zigpy.types as t
from zigpy.typing import UNDEFINED, UndefinedType
from zigpy.zcl import AttributeUpdatedEvent, foundation
from zigpy.zcl.clusters.general import OnOff
from zigpy.zcl.clusters.lighting import Color
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef

from zhaquirks import LocalDataCluster
from zhaquirks.builder import QuirkBuilder, UnitOfTemperature, UnitOfTime
from zhaquirks.clusters import CustomCluster

_LOGGER = logging.getLogger(__name__)

ENDPOINT_ID: Final = 11

# Fallback for the range of the controller, in mireds, until it is read.
NATIVE_MIN_MIREDS: Final = 154
NATIVE_MAX_MIREDS: Final = 500

# The defaults match the native range, so the mapping is transparent until the
# user configures the range of the connected strip.
DEFAULT_WARMEST_K: Final = 2000
DEFAULT_COLDEST_K: Final = 6500
KELVIN_MIN: Final = 1000
KELVIN_MAX: Final = 10000
KELVIN_STEP: Final = 50

# Color loop time in seconds per full loop. The steps follow the values the
# controller uses itself.
COLOR_LOOP_DEFAULT_TIME: Final = 25
COLOR_LOOP_MIN_TIME: Final = 4
COLOR_LOOP_MAX_TIME: Final = 60
COLOR_LOOP_TIME_STEP: Final = 7

# Special values that are not color temperatures and must not be mapped.
START_UP_COLOR_TEMP_PREVIOUS: Final = 0xFFFF
_UNMAPPED_VALUES: Final = (None, 0, START_UP_COLOR_TEMP_PREVIOUS)

_COLOR_TEMP_ATTR_IDS: Final = frozenset(
    {
        Color.AttributeDefs.color_temperature.id,
        Color.AttributeDefs.start_up_color_temperature.id,
    }
)

_RANGE_ATTR_IDS: Final = frozenset(
    {
        Color.AttributeDefs.color_temp_physical_min.id,
        Color.AttributeDefs.color_temp_physical_max.id,
    }
)

_MISSING = object()


def _kelvin_range_to_mireds(warmest_k: Any, coldest_k: Any) -> tuple[int, int]:
    """Convert a Kelvin range to a (min, max) mired range."""
    try:
        warmest = min(max(int(warmest_k), KELVIN_MIN), KELVIN_MAX)
        coldest = min(max(int(coldest_k), KELVIN_MIN), KELVIN_MAX)
    except (TypeError, ValueError):
        return NATIVE_MIN_MIREDS, NATIVE_MAX_MIREDS

    min_mireds, max_mireds = sorted(
        (round(1_000_000 / coldest), round(1_000_000 / warmest))
    )
    if min_mireds == max_mireds:
        return NATIVE_MIN_MIREDS, NATIVE_MAX_MIREDS

    return min_mireds, max_mireds


class GledoptoColorRangeConfigCluster(LocalDataCluster):
    """Local cluster holding the color temperature range of the LED strip.

    The attributes of the local clusters never reach the device. They have no
    manufacturer code, so they are stored and restored by zigpy like standard
    attributes.
    """

    cluster_id: t.uint16_t = 0xFC01
    name: str = "GLEDOPTO Color Range Config"
    ep_attribute: str = "gledopto_range_config"

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        warmest_k: Final = ZCLAttributeDef(
            id=0x0000, type=t.uint16_t, manufacturer_code=None
        )
        coldest_k: Final = ZCLAttributeDef(
            id=0x0001, type=t.uint16_t, manufacturer_code=None
        )

    _DEFAULT_VALUES = {
        AttributeDefs.warmest_k.id: DEFAULT_WARMEST_K,
        AttributeDefs.coldest_k.id: DEFAULT_COLDEST_K,
    }

    @property
    def mireds_range(self) -> tuple[int, int]:
        """Return the configured range as (min, max) mireds."""
        return _kelvin_range_to_mireds(
            self.get(self.AttributeDefs.warmest_k.id),
            self.get(self.AttributeDefs.coldest_k.id),
        )


class GledoptoColorLoopConfigCluster(LocalDataCluster):
    """Local cluster holding the color loop time."""

    cluster_id: t.uint16_t = 0xFC02
    name: str = "GLEDOPTO Color Loop Config"
    ep_attribute: str = "gledopto_color_loop_config"

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        color_loop_time: Final = ZCLAttributeDef(
            id=0x0000, type=t.uint16_t, manufacturer_code=None
        )

    _DEFAULT_VALUES = {
        AttributeDefs.color_loop_time.id: COLOR_LOOP_DEFAULT_TIME,
    }

    async def write_attributes(
        self,
        attributes: dict[str | int | foundation.ZCLAttributeDef, Any],
        manufacturer: int | UndefinedType | None = UNDEFINED,
        **kwargs,
    ) -> list[list[foundation.WriteAttributesStatusRecord]]:
        """Store the color loop time and apply it to a running color loop."""
        result = await super().write_attributes(attributes, manufacturer, **kwargs)

        color = self.endpoint.in_clusters.get(Color.cluster_id)
        if color is None or not color.get(Color.AttributeDefs.color_loop_active.id):
            return result

        loop_time = self.get(self.AttributeDefs.color_loop_time.id)
        _LOGGER.debug("Applying color loop time %s s to running loop", loop_time)

        # The controller ignores a time-only update, so the loop is activated
        # again with the new time.
        await color.color_loop_set(
            update_flags=(
                Color.ColorLoopUpdateFlags.Action | Color.ColorLoopUpdateFlags.Time
            ),
            action=Color.ColorLoopAction.Activate_from_current_hue,
            direction=Color.ColorLoopDirection(
                color.get(Color.AttributeDefs.color_loop_direction.id) or 0
            ),
            time=loop_time,
            start_hue=0,
        )
        return result


class GledoptoColorCluster(CustomCluster, Color):
    """Color cluster that maps the configured range onto the native range."""

    def _virtual_range(self) -> tuple[int, int]:
        """Return the configured range as (min, max) mireds."""
        config = self.endpoint.in_clusters.get(
            GledoptoColorRangeConfigCluster.cluster_id
        )
        if config is None:
            return self._native_range()
        return config.mireds_range

    def _native_range(self) -> tuple[int, int]:
        """Return the range reported by the controller as (min, max) mireds."""
        native_min = super().get(Color.AttributeDefs.color_temp_physical_min.id)
        native_max = super().get(Color.AttributeDefs.color_temp_physical_max.id)
        if (
            isinstance(native_min, int)
            and isinstance(native_max, int)
            and 0 < native_min < native_max
        ):
            return native_min, native_max
        return NATIVE_MIN_MIREDS, NATIVE_MAX_MIREDS

    @staticmethod
    def _map(
        value: float,
        from_range: tuple[int, int],
        to_range: tuple[int, int],
    ) -> int:
        """Map a mired value linearly from one range onto another."""
        ratio = (float(value) - from_range[0]) / (from_range[1] - from_range[0])
        ratio = min(max(ratio, 0.0), 1.0)
        return round(to_range[0] + ratio * (to_range[1] - to_range[0]))

    def _to_native(self, mireds: Any) -> Any:
        """Map a configured-range value to the native range."""
        if mireds in _UNMAPPED_VALUES:
            return mireds
        return self._map(mireds, self._virtual_range(), self._native_range())

    def _to_virtual(self, mireds: Any) -> Any:
        """Map a native value to the configured range."""
        if mireds in _UNMAPPED_VALUES:
            return mireds
        return self._map(mireds, self._native_range(), self._virtual_range())

    def _scale_to_native(self, amount: Any) -> Any:
        """Scale a mired step size or rate to the native range."""
        if not amount:
            return amount
        virtual_min, virtual_max = self._virtual_range()
        native_min, native_max = self._native_range()
        factor = (native_max - native_min) / (virtual_max - virtual_min)
        return max(1, round(amount * factor))

    def _translate_value(self, attr_id: int, value: Any) -> Any:
        """Return the value Home Assistant should see for an attribute."""
        if attr_id == Color.AttributeDefs.color_temp_physical_min.id:
            return self._virtual_range()[0]
        if attr_id == Color.AttributeDefs.color_temp_physical_max.id:
            return self._virtual_range()[1]
        if attr_id in _COLOR_TEMP_ATTR_IDS:
            return self._to_virtual(value)
        return value

    def get(self, key: int | str, default: Any | None = None) -> Any:
        """Return cached values in the configured range."""
        try:
            attr_def = self.find_attribute(key)
        except KeyError:
            return super().get(key, default)

        if attr_def.id in _RANGE_ATTR_IDS:
            return self._translate_value(attr_def.id, None)

        value = super().get(key, _MISSING)
        if value is _MISSING:
            return default
        return self._translate_value(attr_def.id, value)

    async def read_attributes(
        self,
        attributes: list[int | str | foundation.ZCLAttributeDef],
        allow_cache: bool = False,
        only_cache: bool = False,
        manufacturer: int | UndefinedType | None = UNDEFINED,
        **kwargs,
    ) -> Any:
        """Return read values in the configured range.

        The physical limits are answered locally, as they only depend on the
        configured range.
        """
        local = {
            key: self._translate_value(attr_id, None)
            for key in attributes
            if (attr_id := self.find_attribute(key).id) in _RANGE_ATTR_IDS
        }
        remote = [key for key in attributes if key not in local]

        success, failure = {}, {}
        if remote:
            success, failure = await super().read_attributes(
                remote,
                allow_cache=allow_cache,
                only_cache=only_cache,
                manufacturer=manufacturer,
                **kwargs,
            )
        for key, value in success.items():
            success[key] = self._translate_value(self.find_attribute(key).id, value)
        return {**success, **local}, failure

    async def write_attributes(
        self,
        attributes: dict[str | int | foundation.ZCLAttributeDef, Any],
        manufacturer: int | UndefinedType | None = UNDEFINED,
        **kwargs,
    ) -> list[list[foundation.WriteAttributesStatusRecord]]:
        """Map the start-up color temperature to the native range."""
        start_up_id = Color.AttributeDefs.start_up_color_temperature.id
        attributes = {
            key: (
                self._to_native(value)
                if self.find_attribute(key).id == start_up_id
                else value
            )
            for key, value in attributes.items()
        }
        return await super().write_attributes(attributes, manufacturer, **kwargs)

    def _translate_command(self, command_id: int, kwargs: dict[str, Any]) -> None:
        """Map color temperature and color loop command arguments in place."""
        commands = Color.ServerCommandDefs

        if command_id == commands.move_to_color_temp.id:
            kwargs["color_temp_mireds"] = self._to_native(kwargs["color_temp_mireds"])
            return

        if command_id == commands.color_loop_set.id:
            flags = Color.ColorLoopUpdateFlags(kwargs.get("update_flags", 0))
            if Color.ColorLoopUpdateFlags.Action in flags and kwargs.get("action") in (
                Color.ColorLoopAction.Activate_from_color_loop_hue,
                Color.ColorLoopAction.Activate_from_current_hue,
            ):
                config = self.endpoint.in_clusters.get(
                    GledoptoColorLoopConfigCluster.cluster_id
                )
                if config is not None:
                    kwargs["time"] = config.get(
                        GledoptoColorLoopConfigCluster.AttributeDefs.color_loop_time.id
                    )
                    kwargs["update_flags"] = flags | Color.ColorLoopUpdateFlags.Time
            return

        # move_color_temp and step_color_temp. A limit of 0 means "use the
        # physical limit" and is left untouched by _to_native.
        for name in ("color_temp_min_mireds", "color_temp_max_mireds"):
            if name in kwargs:
                kwargs[name] = self._to_native(kwargs[name])
        for name in ("rate", "step_size"):
            if name in kwargs:
                kwargs[name] = self._scale_to_native(kwargs[name])

    async def command(
        self,
        command_id: foundation.GeneralCommand | int | t.uint8_t,
        *args,
        manufacturer: int | t.uint16_t | None = None,
        expect_reply: bool = True,
        **kwargs: Any,
    ):
        """Map color temperature commands and apply the color loop time."""
        if command_id in (
            Color.ServerCommandDefs.move_to_color_temp.id,
            Color.ServerCommandDefs.move_color_temp.id,
            Color.ServerCommandDefs.step_color_temp.id,
            Color.ServerCommandDefs.color_loop_set.id,
        ):
            schema = self.server_commands[command_id].schema
            kwargs = {**dict(zip((f.name for f in schema.fields), args)), **kwargs}
            args = ()
            self._translate_command(command_id, kwargs)

        result = await super().command(
            command_id,
            *args,
            manufacturer=manufacturer,
            expect_reply=expect_reply,
            **kwargs,
        )

        if (
            command_id == Color.ServerCommandDefs.color_loop_set.id
            and getattr(result, "status", None) == foundation.Status.SUCCESS
        ):
            self._update_color_loop_state(kwargs)
        return result

    def _update_color_loop_state(self, kwargs: dict[str, Any]) -> None:
        """Track the color loop state after a successful color loop command.

        ZHA only reads the color loop state on startup, so the cache is updated
        here. The color loop time can then be applied to a running loop.
        """
        flags = Color.ColorLoopUpdateFlags(kwargs.get("update_flags", 0))
        if Color.ColorLoopUpdateFlags.Action in flags:
            self.update_attribute(
                Color.AttributeDefs.color_loop_active.id,
                int(kwargs.get("action") != Color.ColorLoopAction.Deactivate),
            )
        if Color.ColorLoopUpdateFlags.Direction in flags:
            self.update_attribute(
                Color.AttributeDefs.color_loop_direction.id,
                int(kwargs.get("direction", 0)),
            )


class GledoptoLight(Light):
    """Light that follows the configured color temperature range live.

    ZHA reads the color temperature limits once, when the entity is created.
    This light reads them on every state update and sends a state update when
    the configured range changes.
    """

    @property
    def min_mireds(self) -> int:
        """Return the coldest configured color temperature."""
        return self._color_min_mireds

    @property
    def max_mireds(self) -> int:
        """Return the warmest configured color temperature."""
        return self._color_max_mireds

    def on_add(self) -> None:
        """Listen for changes of the configured range."""
        super().on_add()
        config = self.endpoint.zigpy_endpoint.in_clusters.get(
            GledoptoColorRangeConfigCluster.cluster_id
        )
        if config is not None:
            self._on_remove_callbacks.append(
                config.on_event(
                    AttributeUpdatedEvent.event_type, self._handle_range_updated
                )
            )

    def _handle_range_updated(self, event: AttributeUpdatedEvent) -> None:
        """Update the limits and current color temperature in Home Assistant."""
        if self.color_temp is not None:
            self._color_temp = self._color_temperature
        self.maybe_emit_state_changed_event()


(
    QuirkBuilder("GLEDOPTO", "GL-C-008P")
    .replaces(GledoptoColorCluster, endpoint_id=ENDPOINT_ID)
    .adds(GledoptoColorRangeConfigCluster, endpoint_id=ENDPOINT_ID)
    .adds(GledoptoColorLoopConfigCluster, endpoint_id=ENDPOINT_ID)
    .replaces_entity(
        Light,
        GledoptoLight,
        endpoint_id=ENDPOINT_ID,
        cluster_id=OnOff.cluster_id,
    )
    .number(
        attribute_name=GledoptoColorRangeConfigCluster.AttributeDefs.warmest_k.name,
        cluster_id=GledoptoColorRangeConfigCluster.cluster_id,
        endpoint_id=ENDPOINT_ID,
        min_value=KELVIN_MIN,
        max_value=KELVIN_MAX,
        step=KELVIN_STEP,
        unit=UnitOfTemperature.KELVIN,
        mode="box",
        translation_key="warmest_color_temperature",
        fallback_name="Warmest color temperature",
    )
    .number(
        attribute_name=GledoptoColorRangeConfigCluster.AttributeDefs.coldest_k.name,
        cluster_id=GledoptoColorRangeConfigCluster.cluster_id,
        endpoint_id=ENDPOINT_ID,
        min_value=KELVIN_MIN,
        max_value=KELVIN_MAX,
        step=KELVIN_STEP,
        unit=UnitOfTemperature.KELVIN,
        mode="box",
        translation_key="coldest_color_temperature",
        fallback_name="Coldest color temperature",
    )
    .number(
        attribute_name=GledoptoColorLoopConfigCluster.AttributeDefs.color_loop_time.name,
        cluster_id=GledoptoColorLoopConfigCluster.cluster_id,
        endpoint_id=ENDPOINT_ID,
        min_value=COLOR_LOOP_MIN_TIME,
        max_value=COLOR_LOOP_MAX_TIME,
        step=COLOR_LOOP_TIME_STEP,
        unit=UnitOfTime.SECONDS,
        translation_key="color_loop_time",
        fallback_name="Color loop time",
    )
    .add_to_registry()
)
