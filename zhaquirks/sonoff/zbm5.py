"""Sonoff ZBM5 - Zigbee Switch Module."""

from typing import Any, Final

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import EntityPlatform, EntityType, QuirkBuilder
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import OnOff
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef

from zhaquirks.const import (
    BUTTON,
    BUTTON_1,
    BUTTON_2,
    BUTTON_3,
    COMMAND,
    ENDPOINT_ID,
    SHORT_PRESS,
    ZHA_SEND_EVENT,
)

BUTTONS = {1: BUTTON_1, 2: BUTTON_2, 3: BUTTON_3}


class SonoffOnOffCluster(CustomCluster, OnOff):
    """OnOff cluster that emits button press events for toggle commands.

    When the ZBM5 physical button is pressed (especially in decoupled mode),
    the device sends toggle commands to the coordinator. This cluster intercepts
    those commands and emits ZHA events that can trigger Home Assistant automations.
    """

    def handle_cluster_request(
        self,
        hdr: foundation.ZCLHeader,
        args: list[Any],
        *,
        dst_addressing: t.Addressing.Group
        | t.Addressing.IEEE
        | t.Addressing.NWK
        | None = None,
    ):
        """Handle toggle commands from the device and emit button press events."""
        if hdr.command_id == OnOff.ServerCommandDefs.toggle.id:
            button = BUTTONS.get(
                self.endpoint.endpoint_id, f"button_{self.endpoint.endpoint_id}"
            )
            action = f"{button}_{SHORT_PRESS}"
            event_args = {
                BUTTON: button,
                ENDPOINT_ID: self.endpoint.endpoint_id,
            }
            self.listener_event(ZHA_SEND_EVENT, action, event_args)

        return super().handle_cluster_request(hdr, args, dst_addressing=dst_addressing)


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

    SonoffDetachedRelayMask: Final = SonoffDetachedRelayMask

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        work_mode = ZCLAttributeDef(
            id=0x0018,
            type=SonoffWorkMode,
            manufacturer_code=None,
        )
        detach_relay_mask = ZCLAttributeDef(
            id=0x0019,
            type=SonoffDetachedRelayMask,
            manufacturer_code=None,
        )
        relay_1_detached = ZCLAttributeDef(
            id=0x0FFA,
            type=t.Bool,
            manufacturer_code=None,
        )
        relay_2_detached = ZCLAttributeDef(
            id=0x0FFB,
            type=t.Bool,
            manufacturer_code=None,
        )
        relay_3_detached = ZCLAttributeDef(
            id=0x0FFC,
            type=t.Bool,
            manufacturer_code=None,
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
    .replaces(SonoffOnOffCluster)
    .enum(
        SonoffCluster.AttributeDefs.work_mode.name,
        SonoffWorkMode,
        SonoffCluster.cluster_id,
        entity_type=EntityType.DIAGNOSTIC,
        entity_platform=EntityPlatform.SENSOR,
        initially_disabled=True,
        translation_key="work_mode",
        fallback_name="Work mode",
    )
    .switch(
        SonoffCluster.AttributeDefs.relay_1_detached.name,
        SonoffCluster.cluster_id,
        entity_type=EntityType.CONFIG,
        initially_disabled=True,
        translation_key="detach_relay_1",
        fallback_name="Detach relay 1",
    )
    .device_automation_triggers(
        {
            (SHORT_PRESS, BUTTON_1): {COMMAND: f"{BUTTON_1}_{SHORT_PRESS}"},
        }
    )
)
zbm_1c_quirk.add_to_registry()

zbm_2c_quirk = (
    zbm_1c_quirk.clone()
    .applies_to("SONOFF", "ZBM5-2C-80/86")
    .applies_to("SONOFF", "ZBM5-2C-120")
    .replaces(SonoffOnOffCluster, endpoint_id=2)
    .switch(
        SonoffCluster.AttributeDefs.relay_2_detached.name,
        SonoffCluster.cluster_id,
        entity_type=EntityType.CONFIG,
        initially_disabled=True,
        translation_key="detach_relay_2",
        fallback_name="Detach relay 2",
    )
    .device_automation_triggers(
        {
            (SHORT_PRESS, BUTTON_2): {COMMAND: f"{BUTTON_2}_{SHORT_PRESS}"},
        }
    )
)
zbm_2c_quirk.add_to_registry()

zbm_3c_quirk = (
    zbm_2c_quirk.clone()
    .applies_to("SONOFF", "ZBM5-3C-80/86")
    .applies_to("SONOFF", "ZBM5-3C-120")
    .replaces(SonoffOnOffCluster, endpoint_id=3)
    .switch(
        SonoffCluster.AttributeDefs.relay_3_detached.name,
        SonoffCluster.cluster_id,
        entity_type=EntityType.CONFIG,
        initially_disabled=True,
        translation_key="detach_relay_3",
        fallback_name="Detach relay 3",
    )
    .device_automation_triggers(
        {
            (SHORT_PRESS, BUTTON_3): {COMMAND: f"{BUTTON_3}_{SHORT_PRESS}"},
        }
    )
)
zbm_3c_quirk.add_to_registry()
