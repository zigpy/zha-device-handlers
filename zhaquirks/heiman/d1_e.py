"""Heiman smart door sensor D1-E."""

import zigpy.types as t
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef

from zhaquirks.builder import EntityType, QuirkBuilder
from zhaquirks.clusters import CustomCluster


class CustomHeimanCluster(CustomCluster):
    """Heiman custom cluster."""

    cluster_id = 0xFC90

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        alarm_indicator = ZCLAttributeDef(
            id=0x1004,
            type=t.uint8_t,
            manufacturer_code=0x120B,
        )
        rebooted_count = ZCLAttributeDef(
            id=0x0019,
            type=t.uint16_t,
            manufacturer_code=0x120B,
        )
        rejoined_count = ZCLAttributeDef(
            id=0x001A,
            type=t.uint16_t,
            manufacturer_code=0x120B,
        )
        reported_packages = ZCLAttributeDef(
            id=0x001B,
            type=t.uint16_t,
            manufacturer_code=0x120B,
        )


(
    QuirkBuilder()
    .applies_to("Heiman", "D1-E")
    .friendly_name(manufacturer="Heiman", model="Smart door sensor")
    .replaces(CustomHeimanCluster)
    .switch(
        CustomHeimanCluster.AttributeDefs.alarm_indicator.name,
        CustomHeimanCluster.cluster_id,
        translation_key="alarm_indicator",
        fallback_name="Alarm indicator",
    )
    # Zigbee debug sensors:
    .sensor(
        CustomHeimanCluster.AttributeDefs.rebooted_count.name,
        CustomHeimanCluster.cluster_id,
        entity_type=EntityType.DIAGNOSTIC,
        initially_disabled=True,
        translation_key="rebooted_count",
        fallback_name="Rebooted count",
    )
    .sensor(
        CustomHeimanCluster.AttributeDefs.rejoined_count.name,
        CustomHeimanCluster.cluster_id,
        entity_type=EntityType.DIAGNOSTIC,
        initially_disabled=True,
        translation_key="rejoined_count",
        fallback_name="Rejoined count",
    )
    .sensor(
        CustomHeimanCluster.AttributeDefs.reported_packages.name,
        CustomHeimanCluster.cluster_id,
        entity_type=EntityType.DIAGNOSTIC,
        initially_disabled=True,
        translation_key="reported_packages",
        fallback_name="Reported packages",
    )
    .add_to_registry()
)
