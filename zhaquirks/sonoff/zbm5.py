"""Sonoff ZBMINIR2 - Zigbee Switch."""

from typing import Final

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import EntityPlatform, EntityType, QuirkBuilder
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef


class SonoffWorkMode(t.enum8):
    """work mode."""

    EndDevice = 0x00
    Router = 0x01


class SonoffDetachedRelayMask(t.bitmap8):
    """detached relay mask."""

    Relay1 = 0b00000001
    Relay2 = 0b00000010
    Relay3 = 0b00000100


class SonoffCluster(CustomCluster):
    """Custom Sonoff cluster."""

    cluster_id = 0xFC11

    manufacturer_id_override = foundation.ZCLHeader.NO_MANUFACTURER_ID

    SonoffDetachedRelayMask: Final = SonoffDetachedRelayMask

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        work_mode = ZCLAttributeDef(
            id=0x0018,
            type=SonoffWorkMode,
            zcl_type=foundation.DataTypeId.uint8,
            is_manufacturer_specific=True,
        )
        detach_relay_mask = ZCLAttributeDef(
            id=0x0019,
            type=SonoffDetachedRelayMask,
            is_manufacturer_specific=True,
        )
        relay_1_detached = ZCLAttributeDef(
            id=0x0FFA,
            type=t.Bool,
            is_manufacturer_specific=True,
        )
        relay_2_detached = ZCLAttributeDef(
            id=0x0FFB,
            type=t.Bool,
            is_manufacturer_specific=True,
        )
        relay_3_detached = ZCLAttributeDef(
            id=0x0FFC,
            type=t.Bool,
            is_manufacturer_specific=True,
        )

    def _update_attribute(self, attrid, value):
        """Update attribute and handle relay mask conversion."""

        super()._update_attribute(attrid, value)

        if attrid == self.AttributeDefs.detach_relay_mask.id:
            # Convert bitmap to individual relay states
            mask = value

            self._update_attribute(
                self.AttributeDefs.relay_1_detached.id,
                bool(mask & SonoffDetachedRelayMask.Relay1),
            )

            self._update_attribute(
                self.AttributeDefs.relay_2_detached.id,
                bool(mask & SonoffDetachedRelayMask.Relay2),
            )

            self._update_attribute(
                self.AttributeDefs.relay_3_detached.id,
                bool(mask & SonoffDetachedRelayMask.Relay3),
            )

    async def write_attributes(self, attributes, manufacturer=None, **kwargs):
        """Handle writing individual relay attributes by updating the mask."""
        # Check if any individual relay attributes are being written
        mask_attr = self.AttributeDefs.detach_relay_mask.id
        mask = self.get(mask_attr, 0)
        new_attributes = attributes.copy()

        relay_attr_defs = [
            (self.AttributeDefs.relay_1_detached, SonoffDetachedRelayMask.Relay1),
            (self.AttributeDefs.relay_2_detached, SonoffDetachedRelayMask.Relay2),
            (self.AttributeDefs.relay_3_detached, SonoffDetachedRelayMask.Relay3),
        ]

        for attrid, value in attributes.items():
            for attr_def, bit_mask in relay_attr_defs:
                if attrid in (attr_def.id, attr_def.name):
                    new_attributes.pop(attrid)

                    if value:
                        mask |= bit_mask

                    else:
                        mask &= ~bit_mask

                    new_attributes[mask_attr] = mask

                    break

        return await super().write_attributes(new_attributes, manufacturer, **kwargs)


# Base quirk for 1-channel device
zbm_1c_quirk = (
    QuirkBuilder("SONOFF", "ZBM5-1C-80/86")
    .applies_to("SONOFF", "ZBM5-1C-120")
    .adds(SonoffCluster)
    .enum(
        SonoffCluster.AttributeDefs.work_mode.name,
        SonoffWorkMode,
        SonoffCluster.cluster_id,
        translation_key="work_mode",
        fallback_name="Work mode",
        entity_type=EntityType.DIAGNOSTIC,
        entity_platform=EntityPlatform.SENSOR,
        initially_disabled=True,
    )
    .switch(
        SonoffCluster.AttributeDefs.relay_1_detached.name,
        SonoffCluster.cluster_id,
        translation_key="relay_1_detached",
        fallback_name="Detach Relay 1",
        entity_type=EntityType.CONFIG,
        initially_disabled=True,
    )
)
zbm_1c_quirk.add_to_registry()

zbm_2c_quirk = (
    zbm_1c_quirk.clone()
    .applies_to("SONOFF", "ZBM5-2C-80/86")
    .applies_to("SONOFF", "ZBM5-2C-120")
    .switch(
        SonoffCluster.AttributeDefs.relay_2_detached.name,
        SonoffCluster.cluster_id,
        translation_key="relay_2_detached",
        fallback_name="Detach Relay 2",
        entity_type=EntityType.CONFIG,
        initially_disabled=True,
    )
)
zbm_2c_quirk.add_to_registry()

zbm_3c_quirk = (
    zbm_2c_quirk.clone()
    .applies_to("SONOFF", "ZBM5-3C-80/86")
    .applies_to("SONOFF", "ZBM5-3C-120")
    .switch(
        SonoffCluster.AttributeDefs.relay_3_detached.name,
        SonoffCluster.cluster_id,
        translation_key="relay_3_detached",
        fallback_name="Detach Relay 3",
        entity_type=EntityType.CONFIG,
        initially_disabled=True,
    )
)
zbm_3c_quirk.add_to_registry()
