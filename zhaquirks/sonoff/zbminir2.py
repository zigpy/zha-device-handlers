"""Sonoff ZBMINIR2 - Zigbee Switch."""

from zigpy import types
from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef


class CustomSonoffCluster(CustomCluster):
    """Custom Sonoff cluster."""

    cluster_id = 0xFC11

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        ExternalTriggerMode = ZCLAttributeDef(
            name="ExternalTriggerMode",
            id=0x0016,
            type=t.uint8_t,
        )

        DetachRelay = ZCLAttributeDef(
            name="DetachRelay",
            id=0x0017,
            type=t.Bool,
        )

        TurboMode = ZCLAttributeDef(name="TurboMode", id=0x0012, type=t.int16s)

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

    edge_trigger = 0x00
    pluse_trigger = 0x01
    normally_off_follow_trigger = 0x02
    normally_on_follow_trigger = 0x82


(
    QuirkBuilder("SONOFF", "ZBMINIR2")
    .replaces(CustomSonoffCluster)
    .enum(
        CustomSonoffCluster.AttributeDefs.ExternalTriggerMode.name,
        SonoffExternalSwitchTriggerType,
        CustomSonoffCluster.cluster_id,
        fallback_name="External Trigger Mode",
    )
    .switch(
        CustomSonoffCluster.AttributeDefs.TurboMode.name,
        CustomSonoffCluster.cluster_id,
        off_value=9,
        on_value=20,
        fallback_name="Turbo Mode",
    )
    .switch(
        CustomSonoffCluster.AttributeDefs.DetachRelay.name,
        CustomSonoffCluster.cluster_id,
        off_value=0,
        on_value=1,
        fallback_name="Detach Relay",
    )
    .add_to_registry()
)
