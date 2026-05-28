"""Samotech Zigbee dimmer modules.

Covers SM323 (push rotary dimmer), SM309-S (single-channel inline dimmer)
and SM309-S-2CH (two-channel inline dimmer). All three expose the
manufacturer-specific external switch type attribute (0x8803, uint8) on
the Basic cluster: push-button / on-off / 3-way.

Attribute access uses the device's own manufacturer code (0x100B,
Samotech) from the node descriptor.
"""

import zigpy.types as t
from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
from zigpy.quirks.v2.homeassistant import EntityType
from zigpy.zcl.clusters.general import Basic
from zigpy.zcl.foundation import ZCLAttributeDef


class ExternalSwitchType(t.enum8):
    """Wiring style of the external switch input."""

    Push_button = 0x00
    Normal_on_off = 0x01
    Three_way = 0x02


class SamotechBasicCluster(CustomCluster, Basic):
    """Basic cluster with the Samotech external switch type attribute."""

    class AttributeDefs(Basic.AttributeDefs):
        """Attribute definitions including the Samotech private attribute."""

        external_switch_type = ZCLAttributeDef(
            id=0x8803,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )


# SM323 - push rotary dimmer
(
    QuirkBuilder("Samotech", "SM323")
    .replaces(SamotechBasicCluster)
    .enum(
        attribute_name=SamotechBasicCluster.AttributeDefs.external_switch_type.name,
        enum_class=ExternalSwitchType,
        cluster_id=Basic.cluster_id,
        translation_key="external_switch_type",
        fallback_name="External switch type",
        entity_type=EntityType.CONFIG,
    )
    .add_to_registry()
)

# SM309-S - single-channel inline dimmer
(
    QuirkBuilder("Samotech", "SM309-S")
    .replaces(SamotechBasicCluster)
    .enum(
        attribute_name=SamotechBasicCluster.AttributeDefs.external_switch_type.name,
        enum_class=ExternalSwitchType,
        cluster_id=Basic.cluster_id,
        translation_key="external_switch_type",
        fallback_name="External switch type",
        entity_type=EntityType.CONFIG,
    )
    .add_to_registry()
)

# SM309-S-2CH - two-channel inline dimmer
(
    QuirkBuilder("Samotech", "SM309-S-2CH")
    .replaces(SamotechBasicCluster)
    .enum(
        attribute_name=SamotechBasicCluster.AttributeDefs.external_switch_type.name,
        enum_class=ExternalSwitchType,
        cluster_id=Basic.cluster_id,
        translation_key="external_switch_type",
        fallback_name="External switch type",
        entity_type=EntityType.CONFIG,
    )
    .add_to_registry()
)
