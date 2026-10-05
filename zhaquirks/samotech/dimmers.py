"""Samotech Zigbee dimmer modules.

Covers SM323 (push rotary dimmer), SM309-S (single-channel inline dimmer)
and SM309-S-2CH (two-channel inline dimmer). All three expose the
manufacturer-specific external switch type attribute (0x8803, uint8) on
the Basic cluster: push-button / on-off / 3-way.

Attribute access uses the device's own manufacturer code (0x100B,
Samotech) from the node descriptor.
"""

from zigpy.quirks import CustomCluster
import zigpy.types as t
from zigpy.zcl.clusters.general import Basic, LevelControl, OnOff
from zigpy.zcl.foundation import ZCLAttributeDef

from zhaquirks.builder import EntityType, QuirkBuilder


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
#
# The firmware advertises four functional endpoints: endpoints 1 and 2 are the
# two real dimmer channels (device_type 0x0101, Dimmable Light), while
# endpoints 3 and 4 are phantom duplicates (device_type 0xffff) that mirror the
# same On/Off + Level Control clusters. Left in place, ZHA cannot map the
# 0xffff endpoints as lights and instead creates two extra switch entities plus
# duplicate "On level" / "On/Off transition time" / "Power-on behaviour" /
# "Power-on level" config entities. Strip the entity-producing clusters from the
# phantom endpoints so only the two genuine channels remain.
(
    QuirkBuilder("Samotech", "SM309-S-2CH")
    .replaces(SamotechBasicCluster)
    .removes(OnOff.cluster_id, endpoint_id=3)
    .removes(LevelControl.cluster_id, endpoint_id=3)
    .removes(OnOff.cluster_id, endpoint_id=4)
    .removes(LevelControl.cluster_id, endpoint_id=4)
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
