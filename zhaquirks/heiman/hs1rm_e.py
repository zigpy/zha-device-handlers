"""Heiman HS1RM-E smoke sensor."""

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
from zigpy.quirks.v2.homeassistant import EntityType
from zigpy.zcl.clusters.general import DeviceTemperature, OnOffConfiguration


class HeimanDeviceTemperature(CustomCluster, DeviceTemperature):
    """Heiman Device Temperature cluster that scales raw values by 100."""

    def _update_attribute(self, attrid, value):
        # Attribute 0x0000 is current_temperature
        if attrid == self.AttributeDefs.current_temperature.id and value is not None:
            value = value * 100
        super()._update_attribute(attrid, value)


(
    QuirkBuilder()
    .applies_to("HEIMAN", "RelayModule-EF-3.0")
    .friendly_name(manufacturer="HEIMAN", model="HS1RM-E")
    .replaces(HeimanDeviceTemperature)
    # heiman functions
    .enum(
        OnOffConfiguration.AttributeDefs.switch_type.name,
        OnOffConfiguration.SwitchType,
        OnOffConfiguration.cluster_id,
        endpoint_id=1,
        entity_type=EntityType.CONFIG,
        translation_key="switch_type_l1",
        fallback_name="Switch type l1",
    )
    .enum(
        OnOffConfiguration.AttributeDefs.switch_actions.name,
        OnOffConfiguration.SwitchActions,
        OnOffConfiguration.cluster_id,
        endpoint_id=1,
        entity_type=EntityType.CONFIG,
        translation_key="switch_action_l1",
        fallback_name="Switch action l1",
    )
    .enum(
        OnOffConfiguration.AttributeDefs.switch_type.name,
        OnOffConfiguration.SwitchType,
        OnOffConfiguration.cluster_id,
        endpoint_id=2,
        entity_type=EntityType.CONFIG,
        translation_key="switch_type_l2",
        fallback_name="Switch type l2",
    )
    .enum(
        OnOffConfiguration.AttributeDefs.switch_actions.name,
        OnOffConfiguration.SwitchActions,
        OnOffConfiguration.cluster_id,
        endpoint_id=2,
        entity_type=EntityType.CONFIG,
        translation_key="switch_action_l2",
        fallback_name="Switch action l2",
    )
    .add_to_registry()
)
