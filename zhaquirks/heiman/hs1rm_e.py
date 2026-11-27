"""Heiman HS1RM-E relay module."""

from typing import Final

import zigpy.types as t
from zigpy.zcl.clusters.general import DeviceTemperature, OnOffConfiguration
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef

from zhaquirks.builder import EntityType, QuirkBuilder
from zhaquirks.clusters import CustomCluster


class HeimanSwitchType(t.enum8):
    """Heiman switch input type."""

    Toggle = 0x00
    Momentary = 0x01


class HeimanSpecialCluster(CustomCluster):
    """Heiman manufacturer-specific cluster."""

    cluster_id: t.uint16_t = 0xFC90

    class AttributeDefs(BaseAttributeDefs):
        """Heiman manufacturer-specific attributes."""

        switch_type: Final = ZCLAttributeDef(
            id=0x1010, type=HeimanSwitchType, access="rw", manufacturer_code=0x120B
        )


class HeimanDeviceTemperature(CustomCluster, DeviceTemperature):
    """Heiman Device Temperature cluster that scales raw values by 100."""

    def _update_attribute(self, attrid, value):
        """Scale current_temperature to centidegrees for ZHA's /100 divisor."""
        if attrid == self.AttributeDefs.current_temperature.id and value is not None:
            value = value * 100
        super()._update_attribute(attrid, value)


(
    QuirkBuilder()
    .applies_to("HEIMAN", "RelayModule-EF-3.0")
    .friendly_name(manufacturer="HEIMAN", model="HS1RM-E")
    .replaces(HeimanDeviceTemperature)
    .adds(HeimanSpecialCluster, endpoint_id=1)
    .adds(HeimanSpecialCluster, endpoint_id=2)
    # ZHA splits each channel into a child device, whose name tells the channels
    # apart, so the entity names don't number them
    # switch input type (Heiman manufacturer-specific cluster 0xFC90)
    .enum(
        attribute_name=HeimanSpecialCluster.AttributeDefs.switch_type.name,
        enum_class=HeimanSwitchType,
        cluster_id=HeimanSpecialCluster.cluster_id,
        endpoint_id=1,
        entity_type=EntityType.CONFIG,
        translation_key="switch_type",
        fallback_name="Switch type",
    )
    .enum(
        attribute_name=HeimanSpecialCluster.AttributeDefs.switch_type.name,
        enum_class=HeimanSwitchType,
        cluster_id=HeimanSpecialCluster.cluster_id,
        endpoint_id=2,
        entity_type=EntityType.CONFIG,
        translation_key="switch_type",
        fallback_name="Switch type",
    )
    # switch actions (standard ZCL OnOffConfiguration cluster)
    .enum(
        attribute_name=OnOffConfiguration.AttributeDefs.switch_actions.name,
        enum_class=OnOffConfiguration.SwitchActions,
        cluster_id=OnOffConfiguration.cluster_id,
        endpoint_id=1,
        entity_type=EntityType.CONFIG,
        translation_key="switch_actions",
        fallback_name="Switch actions",
    )
    .enum(
        attribute_name=OnOffConfiguration.AttributeDefs.switch_actions.name,
        enum_class=OnOffConfiguration.SwitchActions,
        cluster_id=OnOffConfiguration.cluster_id,
        endpoint_id=2,
        entity_type=EntityType.CONFIG,
        translation_key="switch_actions",
        fallback_name="Switch actions",
    )
    .add_to_registry()
)
