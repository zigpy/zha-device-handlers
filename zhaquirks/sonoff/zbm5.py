"""Sonoff ZBM5 - Zigbee Switch Module."""

from typing import Any, Final

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import EntityPlatform, EntityType, QuirkBuilder
import zigpy.types as t
from zigpy.zcl import (
    AttributeReadEvent,
    AttributeReportedEvent,
    AttributeUpdatedEvent,
    AttributeWrittenEvent,
    ClusterType,
)
from zigpy.zcl.clusters.general import OnOff
from zigpy.zcl.foundation import BaseAttributeDefs, Status, ZCLAttributeDef

from zhaquirks import LocalDataCluster
from zhaquirks.const import (
    BUTTON_1,
    BUTTON_2,
    BUTTON_3,
    COMMAND,
    COMMAND_TOGGLE,
    ENDPOINT_ID,
    SHORT_PRESS,
)


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

    def __init__(self, *args, **kwargs):
        """Init and listen for mask attribute changes."""
        super().__init__(*args, **kwargs)
        self.on_event(AttributeReadEvent.event_type, self._handle_mask_change)
        self.on_event(AttributeReportedEvent.event_type, self._handle_mask_change)
        self.on_event(AttributeUpdatedEvent.event_type, self._handle_mask_change)
        self.on_event(AttributeWrittenEvent.event_type, self._handle_mask_change)

    def _handle_mask_change(
        self,
        event: AttributeReadEvent
        | AttributeReportedEvent
        | AttributeUpdatedEvent
        | AttributeWrittenEvent,
    ) -> None:
        """Sync relay states to local config cluster on mask change."""
        if isinstance(event, AttributeWrittenEvent) and event.status != Status.SUCCESS:
            return
        if event.attribute_id == self.AttributeDefs.detach_relay_mask.id:
            self.endpoint.sonoff_input_config.update_relay_states(event.value)

    async def apply_custom_configuration(self, *args, **kwargs):
        """Read detach_relay_mask during pairing to populate local relay states."""
        # XXX: We should have a quirks v2 API for adding attributes to ZCL_INIT_ATTRS
        await self.read_attributes([self.AttributeDefs.detach_relay_mask.id])


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

    _DEFAULT_VALUES = {
        AttributeDefs.relay_1_detached.id: t.Bool.false,
        AttributeDefs.relay_2_detached.id: t.Bool.false,
        AttributeDefs.relay_3_detached.id: t.Bool.false,
    }

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
    .adds(OnOff, cluster_type=ClusterType.Client)
    .prevent_default_entity_creation(
        endpoint_id=1,
        cluster_id=OnOff.cluster_id,
        function=lambda entity: entity.device_class == "opening",
    )
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
        translation_key="detach_relay_id",
        fallback_name="Detach relay 1",
        translation_placeholders={"id": "1"},
    )
    .device_automation_triggers(
        {(SHORT_PRESS, BUTTON_1): {COMMAND: COMMAND_TOGGLE, ENDPOINT_ID: 1}}
    )
)
zbm_1c_quirk.add_to_registry()

zbm_2c_quirk = (
    zbm_1c_quirk.clone()
    .applies_to("SONOFF", "ZBM5-2C-80/86")
    .applies_to("SONOFF", "ZBM5-2C-120")
    .adds(OnOff, endpoint_id=2, cluster_type=ClusterType.Client)
    .prevent_default_entity_creation(
        endpoint_id=2,
        cluster_id=OnOff.cluster_id,
        function=lambda entity: entity.device_class == "opening",
    )
    .switch(
        SonoffInputConfigCluster.AttributeDefs.relay_2_detached.name,
        SonoffInputConfigCluster.cluster_id,
        translation_key="detach_relay_id",
        fallback_name="Detach relay 2",
        translation_placeholders={"id": "2"},
    )
    .device_automation_triggers(
        {(SHORT_PRESS, BUTTON_2): {COMMAND: COMMAND_TOGGLE, ENDPOINT_ID: 2}}
    )
)
zbm_2c_quirk.add_to_registry()

zbm_3c_quirk = (
    zbm_2c_quirk.clone()
    .applies_to("SONOFF", "ZBM5-3C-80/86")
    .applies_to("SONOFF", "ZBM5-3C-120")
    .adds(OnOff, endpoint_id=3, cluster_type=ClusterType.Client)
    .prevent_default_entity_creation(
        endpoint_id=3,
        cluster_id=OnOff.cluster_id,
        function=lambda entity: entity.device_class == "opening",
    )
    .switch(
        SonoffInputConfigCluster.AttributeDefs.relay_3_detached.name,
        SonoffInputConfigCluster.cluster_id,
        translation_key="detach_relay_id",
        fallback_name="Detach relay 3",
        translation_placeholders={"id": "3"},
    )
    .device_automation_triggers(
        {(SHORT_PRESS, BUTTON_3): {COMMAND: COMMAND_TOGGLE, ENDPOINT_ID: 3}}
    )
)
zbm_3c_quirk.add_to_registry()
