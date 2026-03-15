"""Sonoff ZBM5 - Zigbee Switch Module."""

from typing import Any, Final

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import EntityPlatform, EntityType, QuirkBuilder
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import OnOff
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef

from zhaquirks import LocalDataCluster
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
    """Custom Sonoff cluster for real device attributes."""

    cluster_id = 0xFC11
    ep_attribute = "sonoff_cluster"

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

    def _update_attribute(
        self, attrid: int | t.uint16_t | ZCLAttributeDef, value: Any
    ) -> None:
        """Update attribute and sync relay states to local config cluster."""
        super()._update_attribute(attrid, value)

        if self.find_attribute(attrid) == self.AttributeDefs.detach_relay_mask:
            self.endpoint.sonoff_input_config.update_relay_states(value)


class SonoffInputConfigCluster(LocalDataCluster):
    """Local cluster for individual relay detach switches."""

    cluster_id = 0xFBFE
    ep_attribute = "sonoff_input_config"

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        relay_1_detached: Final = ZCLAttributeDef(id=0x0000, type=t.Bool)
        relay_2_detached: Final = ZCLAttributeDef(id=0x0001, type=t.Bool)
        relay_3_detached: Final = ZCLAttributeDef(id=0x0002, type=t.Bool)

    _RELAY_BITS: dict[int, int] = {
        AttributeDefs.relay_1_detached.id: SonoffDetachedRelayMask.Relay1,
        AttributeDefs.relay_2_detached.id: SonoffDetachedRelayMask.Relay2,
        AttributeDefs.relay_3_detached.id: SonoffDetachedRelayMask.Relay3,
    }

    def __init__(self, *args, **kwargs):
        """Init with all relays attached by default."""
        super().__init__(*args, **kwargs)
        # TODO: This currently won't work after a HA restart due to a zigpy change,
        #  we should just use _DEFAULT_VALUES when that's ready
        for attr_id in self._RELAY_BITS:
            if attr_id not in self._attr_cache:
                self._update_attribute(attr_id, t.Bool.false)

    def update_relay_states(self, mask: int) -> None:
        """Update individual relay states from a bitmap mask."""
        for attr_id, bit in self._RELAY_BITS.items():
            self._update_attribute(attr_id, bool(mask & bit))

    async def write_attributes(
        self,
        attributes: dict[str | int | ZCLAttributeDef, Any],
        **kwargs,
    ) -> list:
        """Translate per-relay writes into a mask write on real SonoffCluster."""
        mask_attr_id = SonoffCluster.AttributeDefs.detach_relay_mask.id
        mask = self.endpoint.sonoff_cluster.get(mask_attr_id, 0)

        for attr, value in attributes.items():
            bit = self._RELAY_BITS.get(self.find_attribute(attr).id)
            if bit is not None:
                if value:
                    mask |= bit
                else:
                    mask &= ~bit

        return await self.endpoint.sonoff_cluster.write_attributes({mask_attr_id: mask})


# Base quirk for 1-channel device
zbm_1c_quirk = (
    QuirkBuilder("SONOFF", "ZBM5-1C-80/86")
    .applies_to("SONOFF", "ZBM5-1C-120")
    .replaces(SonoffCluster)
    .adds(SonoffInputConfigCluster)
    .replaces(SonoffOnOffCluster)
    .enum(
        SonoffCluster.AttributeDefs.work_mode.name,
        SonoffWorkMode,
        SonoffCluster.cluster_id,
        entity_type=EntityType.DIAGNOSTIC,
        entity_platform=EntityPlatform.SENSOR,
        translation_key="work_mode",
        fallback_name="Work mode",
    )
    .switch(
        SonoffInputConfigCluster.AttributeDefs.relay_1_detached.name,
        SonoffInputConfigCluster.cluster_id,
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
        SonoffInputConfigCluster.AttributeDefs.relay_2_detached.name,
        SonoffInputConfigCluster.cluster_id,
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
        SonoffInputConfigCluster.AttributeDefs.relay_3_detached.name,
        SonoffInputConfigCluster.cluster_id,
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
