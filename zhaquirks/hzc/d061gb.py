"""Quirk for HZC D061-GB dimmer with power metering."""

import logging
from typing import Final

from zigpy import types as t
from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
from zigpy.quirks.v2.homeassistant import PERCENTAGE
from zigpy.typing import UNDEFINED, UndefinedType
from zigpy.zcl.clusters.general import LevelControl, OnOff
from zigpy.zcl.foundation import ZCLAttributeDef

_LOGGER = logging.getLogger(__name__)


class DimmingMode(t.enum8):
    """Dimming mode (output edge type)."""

    trailing_edge = 0x00
    leading_edge = 0x01


class ExternalSwitchType(t.enum8):
    """External switch type."""

    door_bell = 0x00
    normal_switch = 0x01


class DimmerWorkMode(t.enum8):
    """Dimmer work mode."""

    dimmer = 0x00
    switch = 0x01


class HzcLevelControl(CustomCluster, LevelControl):
    """HZC level control cluster with private attributes."""

    # Wire attribute is 0-254, but the UI exposes it as 0-100%.
    _ON_LEVEL_WIRE_MAX = 254

    @staticmethod
    def wire_to_percent(value: int) -> int:
        """Convert the raw on_level to 0-100 percent.

        Raw 255 is the device's "off" sentinel and is shown as 0%.
        """
        if value == 255:
            return 0
        return round(value * 100 / HzcLevelControl._ON_LEVEL_WIRE_MAX)

    @staticmethod
    def percent_to_wire(value: int) -> int:
        """Convert a 0-100 percent back to the raw on_level.

        UI 0% is sent to the device as 255 (its "off" sentinel).
        """
        if value == 0:
            return 255
        return round(value * HzcLevelControl._ON_LEVEL_WIRE_MAX / 100)

    @staticmethod
    def wire_to_percent_start(value: int) -> int:
        """Convert the raw start_level to 0-100 percent.

        start_level's usable range is 1-254 (value 0 is treated as 1 by the
        device), so this is a plain linear 0-254 mapping with no "off" sentinel.
        """
        return round(value * 100 / HzcLevelControl._ON_LEVEL_WIRE_MAX)

    @staticmethod
    def percent_to_wire_start(value: int) -> int:
        """Convert a 0-100 percent back to the raw start_level (1-254)."""
        return round(value * HzcLevelControl._ON_LEVEL_WIRE_MAX / 100)

    def _update_attribute(self, attrid, value):
        # Report on_level/start_level to ZHA in percent so the number entities
        # read cleanly; the raw 0-254 value is only used on the wire.
        if value is not None:
            if attrid == LevelControl.AttributeDefs.on_level.id:
                value = self.wire_to_percent(value)
            elif attrid == HzcLevelControl.AttributeDefs.start_level.id:
                value = self.wire_to_percent_start(value)
        super()._update_attribute(attrid, value)

    async def write_attributes(
        self,
        attributes: dict[str | int | ZCLAttributeDef, object],
        manufacturer: int | UndefinedType | None = UNDEFINED,
        **kwargs,
    ) -> object:
        """Write attributes, translating 0-100% UI values to raw wire values."""
        # Translate the 0-100% UI value to the raw value the device expects.
        # on_level keeps a 0xFF "off" sentinel; start_level is a plain 0-254.
        if "on_level" in attributes and attributes["on_level"] is not None:
            attributes = {
                **attributes,
                "on_level": self.percent_to_wire(attributes["on_level"]),
            }
        if "start_level" in attributes and attributes["start_level"] is not None:
            attributes = {
                **attributes,
                "start_level": self.percent_to_wire_start(attributes["start_level"]),
            }

        result = await super().write_attributes(
            attributes,
            manufacturer=manufacturer,
            **kwargs,
        )

        # super() caches the raw value after a write; re-run it through
        # _update_attribute so the attribute cache stays in 0-100% (this also
        # works whether the cache is an AttributeCache or a plain dict).
        if attributes.get("on_level") is not None:
            self._update_attribute(
                LevelControl.AttributeDefs.on_level.id, attributes["on_level"]
            )
        if attributes.get("start_level") is not None:
            self._update_attribute(
                HzcLevelControl.AttributeDefs.start_level.id, attributes["start_level"]
            )

        return result

    class AttributeDefs(LevelControl.AttributeDefs):
        """HZC private attributes on the level control cluster."""

        # Writable on this device, unlike the read-only ZCL defaults
        min_level: Final = ZCLAttributeDef(id=0x0002, type=t.uint8_t, access="rw")
        max_level: Final = ZCLAttributeDef(id=0x0003, type=t.uint8_t, access="rw")
        out_edge: Final = ZCLAttributeDef(id=0xB000, type=DimmingMode)
        # Written as plain uint8, not enum8, per the manufacturer driver;
        # the enum is still exposed via the select entity below.
        external_switch_type: Final = ZCLAttributeDef(id=0xB003, type=t.uint8_t)
        # Written as plain uint8, not enum8, per the manufacturer driver;
        # the enum is still exposed via the select entity below.
        dimmer_work_mode: Final = ZCLAttributeDef(id=0xB004, type=t.uint8_t)
        start_level: Final = ZCLAttributeDef(id=0xB005, type=t.uint8_t)


(
    QuirkBuilder("HZC", "D061-GB")
    .replaces(HzcLevelControl)
    .prevent_default_entity_creation(
        endpoint_id=1,
        cluster_id=OnOff.cluster_id,
        function=lambda entity: entity.__class__.__name__ == "StartupOnOffSelectEntity",
    )
    .enum(
        attribute_name=OnOff.AttributeDefs.start_up_on_off.name,
        enum_class=OnOff.StartUpOnOff,
        cluster_id=OnOff.cluster_id,
        endpoint_id=1,
        translation_key="start_up_on_off",
        fallback_name="Power on state",
    )
    .prevent_default_entity_creation(
        endpoint_id=1,
        cluster_id=HzcLevelControl.cluster_id,
        function=lambda entity: (
            entity.__class__.__name__ == "OnLevelConfigurationEntity"
        ),
    )
    .number(
        attribute_name=LevelControl.AttributeDefs.on_level.name,
        cluster_id=HzcLevelControl.cluster_id,
        endpoint_id=1,
        min_value=0,
        max_value=100,
        step=1,
        unit=PERCENTAGE,
        translation_key="on_level",
        fallback_name="On level",
    )
    .number(
        attribute_name=LevelControl.AttributeDefs.min_level.name,
        cluster_id=HzcLevelControl.cluster_id,
        endpoint_id=1,
        min_value=1,
        max_value=50,
        step=1,
        unit=PERCENTAGE,
        attribute_initialized_from_cache=False,
        translation_key="min_level",
        fallback_name="Minimum brightness",
    )
    .number(
        attribute_name=LevelControl.AttributeDefs.max_level.name,
        cluster_id=HzcLevelControl.cluster_id,
        endpoint_id=1,
        min_value=50,
        max_value=100,
        step=1,
        unit=PERCENTAGE,
        attribute_initialized_from_cache=False,
        translation_key="max_level",
        fallback_name="Maximum brightness",
    )
    .enum(
        attribute_name="out_edge",
        enum_class=DimmingMode,
        cluster_id=HzcLevelControl.cluster_id,
        endpoint_id=1,
        translation_key="dimming_mode",
        fallback_name="Dimming mode",
    )
    .enum(
        attribute_name="external_switch_type",
        enum_class=ExternalSwitchType,
        cluster_id=HzcLevelControl.cluster_id,
        endpoint_id=1,
        attribute_initialized_from_cache=False,
        translation_key="external_switch_type",
        fallback_name="External switch type",
    )
    .enum(
        attribute_name="dimmer_work_mode",
        enum_class=DimmerWorkMode,
        cluster_id=HzcLevelControl.cluster_id,
        endpoint_id=1,
        attribute_initialized_from_cache=False,
        translation_key="dimmer_work_mode",
        fallback_name="Dimmer work mode",
    )
    .number(
        attribute_name="start_level",
        cluster_id=HzcLevelControl.cluster_id,
        endpoint_id=1,
        min_value=0,
        max_value=100,
        step=1,
        unit=PERCENTAGE,
        attribute_initialized_from_cache=False,
        translation_key="start_level",
        fallback_name="Start level",
    )
    .prevent_default_entity_creation(
        endpoint_id=1,
        cluster_id=HzcLevelControl.cluster_id,
        function=lambda entity: (
            entity.__class__.__name__ == "DefaultMoveRateConfigurationEntity"
        ),
    )
    .number(
        attribute_name=LevelControl.AttributeDefs.default_move_rate.name,
        cluster_id=HzcLevelControl.cluster_id,
        endpoint_id=1,
        min_value=1,
        max_value=10,
        step=1,
        translation_key="default_move_rate",
        fallback_name="Default move rate",
    )
    .add_to_registry()
)
