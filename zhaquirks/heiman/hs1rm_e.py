"""Heiman HS1RM-E smoke sensor."""

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
from zigpy.quirks.v2.homeassistant import EntityType
import zigpy.types as t
from zigpy.zcl.clusters.general import DeviceTemperature
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef


class SwitchTypeEnum(t.enum8):
    """switch type type."""

    Toggle = 0
    Momentary = 1


class SwitchActionEnum(t.enum8):
    """switch action type."""

    State1_to_state2 = 0
    State2_to_state1 = 1
    Toggle = 2


class OnoffSwitchConfigurationCluster(CustomCluster):
    """On/Off Switch Configuration cluster."""

    cluster_id = 0x0007

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        switch_type = ZCLAttributeDef(
            id=0x0000,
            type=t.enum8,
        )
        switch_actions = ZCLAttributeDef(
            id=0x0010,
            type=t.enum8,
        )


class HeimanDeviceTemperature(CustomCluster, DeviceTemperature):
    """Heiman Device Temperature cluster that scales raw values by 100."""

    def _update_attribute(self, attrid, value):
        # Attribute 0x0000 is current_temperature
        if attrid == 0x0000 and value is not None:
            value = value * 100
        super()._update_attribute(attrid, value)


(
    QuirkBuilder()
    .applies_to("HEIMAN", "RelayModule-EF-3.0")
    .friendly_name(manufacturer="HEIMAN", model="HS1RM-E")
    .replaces(OnoffSwitchConfigurationCluster)
    .replaces(HeimanDeviceTemperature)
    # heiman functions
    .enum(
        OnoffSwitchConfigurationCluster.AttributeDefs.switch_type.name,
        SwitchTypeEnum,
        OnoffSwitchConfigurationCluster.cluster_id,
        endpoint_id=1,
        entity_type=EntityType.CONFIG,
        translation_key="switch_type_l1",
        fallback_name="Switch type l1",
    )
    .enum(
        OnoffSwitchConfigurationCluster.AttributeDefs.switch_actions.name,
        SwitchActionEnum,
        OnoffSwitchConfigurationCluster.cluster_id,
        endpoint_id=1,
        entity_type=EntityType.CONFIG,
        translation_key="switch_action_l1",
        fallback_name="Switch action l1",
    )
    .enum(
        OnoffSwitchConfigurationCluster.AttributeDefs.switch_type.name,
        SwitchTypeEnum,
        OnoffSwitchConfigurationCluster.cluster_id,
        endpoint_id=2,
        entity_type=EntityType.CONFIG,
        translation_key="switch_type_l2",
        fallback_name="Switch type l2",
    )
    .enum(
        OnoffSwitchConfigurationCluster.AttributeDefs.switch_actions.name,
        SwitchActionEnum,
        OnoffSwitchConfigurationCluster.cluster_id,
        endpoint_id=2,
        entity_type=EntityType.CONFIG,
        translation_key="switch_action_l2",
        fallback_name="Switch action l2",
    )
    .add_to_registry()
)
