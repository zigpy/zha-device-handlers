"""Quirk for PushOk POK006 zigbee garden valve.

Maps MultistateInput (0x0012) present_value → valve status enum sensor
Maps MultistateValue (0x0014) present_value → stall time number
"""

import enum

from zigpy.quirks.v2 import QuirkBuilder
from zigpy.quirks.v2.homeassistant import EntityPlatform, EntityType
from zigpy.zcl.clusters.general import MultistateInput, MultistateValue


class ValveStatus(enum.IntEnum):
    OFF = 0
    ON = 1
    MOVING = 2
    STUCK = 3


(
    QuirkBuilder("PushOk Hardware", "POK006")
    .enum(
        attribute_name="present_value",
        unique_id_suffix="valve_status",
        enum_class=ValveStatus,
        cluster_id=MultistateInput.cluster_id,
        endpoint_id=1,
        entity_platform=EntityPlatform.SENSOR,
        entity_type=EntityType.STANDARD,
        fallback_name="Valve status",
        translation_key="valve_status",
        initially_disabled=False,
    )
    .number(
        attribute_name="present_value",
        unique_id_suffix="stall_time",
        cluster_id=MultistateValue.cluster_id,
        endpoint_id=1,
        min_value=0,
        max_value=60,
        step=1,
        unit="s",
        entity_type=EntityType.CONFIG,
        fallback_name="Stall time",
        translation_key="stall_time",
        initially_disabled=False,
    )
    .add_to_registry()
)
