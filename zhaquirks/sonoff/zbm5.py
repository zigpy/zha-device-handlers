"""Sonoff ZBM5 - Zigbee Switch Module."""

from typing import Any

from zha.application.platforms import AttrConfig, ClusterConfig
from zha.application.platforms.switch import ConfigurableAttributeSwitch
import zigpy.types as t
from zigpy.zcl import ClusterType
from zigpy.zcl.clusters.general import OnOff
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef

from zhaquirks.builder import EntityPlatform, EntityType, QuirkBuilder
from zhaquirks.clusters import CustomCluster
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


class DetachRelaySwitch(ConfigurableAttributeSwitch):
    """Switch for one relay bit of `detach_relay_mask`."""

    _attribute_name = SonoffCluster.AttributeDefs.detach_relay_mask.name
    _server_cluster_config = {
        SonoffCluster.cluster_id: ClusterConfig(
            attributes={
                SonoffCluster.AttributeDefs.detach_relay_mask: AttrConfig(
                    read_on_startup=True
                ),
            },
        ),
    }

    def __init__(
        self, *args: Any, relay: SonoffDetachedRelayMask, **kwargs: Any
    ) -> None:
        """Init the switch for the given relay."""
        self._relay = relay
        super().__init__(*args, **kwargs)

    @property
    def is_on(self) -> bool:
        """Return if the relay is detached."""
        mask = self._cluster.get(self._attribute_name)
        return mask is not None and self._relay in mask

    async def async_turn_on_off(self, state: bool) -> None:
        """Detach or attach the relay."""
        mask = self._cluster.get(self._attribute_name)
        mask = (mask | self._relay) if state else (mask & ~self._relay)

        await self._cluster.write_attributes({self._attribute_name: mask})
        self.maybe_emit_state_changed_event()


# Base quirk for 1-channel device
zbm_1c_quirk = (
    QuirkBuilder("SONOFF", "ZBM5-1C-80/86")
    .applies_to("SONOFF", "ZBM5-1C-120")
    .replaces(SonoffCluster)
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
    .adds_entity(
        DetachRelaySwitch,
        endpoint_id=1,
        cluster_id=SonoffCluster.cluster_id,
        relay=SonoffDetachedRelayMask.Relay1,
        unique_id_suffix="relay_1_detached",
        translation_key="detach_relay_id",
        translation_placeholders={"id": "1"},
        fallback_name="Detach relay 1",
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
    .adds_entity(
        DetachRelaySwitch,
        endpoint_id=1,
        cluster_id=SonoffCluster.cluster_id,
        relay=SonoffDetachedRelayMask.Relay2,
        unique_id_suffix="relay_2_detached",
        translation_key="detach_relay_id",
        translation_placeholders={"id": "2"},
        fallback_name="Detach relay 2",
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
    .adds_entity(
        DetachRelaySwitch,
        endpoint_id=1,
        cluster_id=SonoffCluster.cluster_id,
        relay=SonoffDetachedRelayMask.Relay3,
        unique_id_suffix="relay_3_detached",
        translation_key="detach_relay_id",
        translation_placeholders={"id": "3"},
        fallback_name="Detach relay 3",
    )
    .device_automation_triggers(
        {(SHORT_PRESS, BUTTON_3): {COMMAND: COMMAND_TOGGLE, ENDPOINT_ID: 3}}
    )
)
zbm_3c_quirk.add_to_registry()
