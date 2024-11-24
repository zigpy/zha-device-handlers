"""Sonoff ZBMINIR2 - Zigbee Switch."""

from zigpy import types
from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef


class SonoffCluster(CustomCluster):
    """Custom Sonoff cluster."""

    cluster_id = 0xFC11

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        external_trigger_mode = ZCLAttributeDef(
            id=0x0016,
            type=t.uint8_t,
        )
        detach_relay = ZCLAttributeDef(
            id=0x0017,
            type=t.Bool,
        )
        turbo_mode = ZCLAttributeDef(
            id=0x0012,
            type=t.int16s,
        )

    async def _read_attributes(
        self,
        attribute_ids: list[t.uint16_t],
        *args,
        manufacturer: int | t.uint16_t | None = None,
        **kwargs,
    ):
        """Read attributes ZCL foundation command."""
        return await super()._read_attributes(
            attribute_ids,
            *args,
            manufacturer=foundation.ZCLHeader.NO_MANUFACTURER_ID,
            **kwargs,
        )

    @property
    def _is_manuf_specific(self):
        return False


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
