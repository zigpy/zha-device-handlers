"""Sonoff ZBMINIR2 - Zigbee Switch."""

from zigpy import types
from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef, ZCLCommandDef
from typing import Any, Final
import logging
_LOGGER = logging.getLogger(__name__)

class SonoffCluster(CustomCluster):
    """Custom Sonoff cluster."""

    cluster_id = 0xFC11

    manufacturer_id_override = foundation.ZCLHeader.NO_MANUFACTURER_ID

    class ClientCommandDefs(BaseAttributeDefs):
        """Client command definitions."""

        toggle: Final = ZCLCommandDef(
            id=0x02,
            schema={},
            is_manufacturer_specific=True,
        )

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        external_trigger_mode = ZCLAttributeDef(
            id=0x0016,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        detach_relay = ZCLAttributeDef(
            id=0x0017,
            type=t.Bool,
            is_manufacturer_specific=True,
        )
        turbo_mode = ZCLAttributeDef(
            id=0x0012,
            type=t.int16s,
            is_manufacturer_specific=True,
        )

    async def _read_attributes(
            self,
            attribute_ids: list[t.uint16_t],
            *args,
            manufacturer: int | t.uint16_t | None = None,
            **kwargs,
    ):
        _LOGGER.info(f"read_attributes: {manufacturer}")
        return await super()._read_attributes(
            attribute_ids, *args, manufacturer=manufacturer, **kwargs
        )

    async def _write_attributes(  # type:ignore[override]
            self,
            attributes: list[foundation.Attribute],
            *args,
            manufacturer: int | t.uint16_t | None = None,
            **kwargs,
    ):
        _LOGGER.info(f"write_attributes: {manufacturer}")
        return await super()._write_attributes(
            attributes, *args, manufacturer=manufacturer, **kwargs
        )


class SonoffExternalSwitchTriggerType(types.enum8):
    """extern switch trigger type."""

    Edge_trigger = 0x00
    Pulse_trigger = 0x01
    Normally_off_follow_trigger = 0x02
    Normally_on_follow_trigger = 0x82


(
    QuirkBuilder("SONOFF", "ZBMINIR2")
    .replaces(SonoffCluster)
    .enum(
        SonoffCluster.AttributeDefs.external_trigger_mode.name,
        SonoffExternalSwitchTriggerType,
        SonoffCluster.cluster_id,
        translation_key="external_trigger_mode",
        fallback_name="External trigger mode",
    )
    .switch(
        SonoffCluster.AttributeDefs.turbo_mode.name,
        SonoffCluster.cluster_id,
        off_value=9,
        on_value=20,
        translation_key="turbo_mode",
        fallback_name="Turbo mode",
    )
    .switch(
        SonoffCluster.AttributeDefs.detach_relay.name,
        SonoffCluster.cluster_id,
        off_value=0,
        on_value=1,
        translation_key="detach_relay",
        fallback_name="Detach relay",
    )
    .add_to_registry()
)
