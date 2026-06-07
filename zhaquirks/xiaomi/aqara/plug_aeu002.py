"""Aqara Wall Outlet H2 UK (lumi.plug.aeu002 / WP-P09D).

A three-output mains outlet: socket 1 (endpoint 1), socket 2 (endpoint 2) and
USB (endpoint 3). Sockets 1 and 2 have a physical button that reports press
actions over genMultistateInput. Attribute IDs and value mappings for the
manufacturer-specific cluster (0xFCC0) are ported from the
zigbee-herdsman-converters definition for this model.
"""

from __future__ import annotations

from zigpy import types as t
from zigpy.quirks.v2 import QuirkBuilder
from zigpy.quirks.v2.homeassistant import EntityType, UnitOfPower
from zigpy.quirks.v2.homeassistant.number import NumberDeviceClass
from zigpy.zcl.clusters.general import MultistateInput
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef

from zhaquirks.const import (
    BUTTON_1,
    BUTTON_2,
    COMMAND,
    DOUBLE_PRESS,
    LONG_PRESS,
    LONG_RELEASE,
    SHORT_PRESS,
)
from zhaquirks.xiaomi import LUMI, XiaomiAqaraE1Cluster
from zhaquirks.xiaomi.aqara.opple_remote import (
    COMMAND_1_DOUBLE,
    COMMAND_1_HOLD,
    COMMAND_1_RELEASE,
    COMMAND_1_SINGLE,
    COMMAND_2_DOUBLE,
    COMMAND_2_HOLD,
    COMMAND_2_RELEASE,
    COMMAND_2_SINGLE,
    MultistateInputCluster,
)

XIAOMI_MFG_CODE = 0x115F

# Overload protection range in watts, ported from the zigbee-herdsman-converters
# definition for lumi.plug.aeu002 (numeric min 100, max 3840).
OVERLOAD_PROTECTION_MIN_WATTS = 100
OVERLOAD_PROTECTION_MAX_WATTS = 3840


class AqaraPlugH2Cluster(XiaomiAqaraE1Cluster):
    """Aqara manufacturer cluster for the H2 wall outlet."""

    class AttributeDefs(BaseAttributeDefs):
        """Manufacturer specific attributes."""

        power_outage_memory = ZCLAttributeDef(
            id=0x0201,
            type=t.Bool,
            access="rwp",
            manufacturer_code=XIAOMI_MFG_CODE,
        )

        led_indicator = ZCLAttributeDef(
            id=0x0203,
            type=t.Bool,
            access="rwp",
            manufacturer_code=XIAOMI_MFG_CODE,
        )

        overload_protection = ZCLAttributeDef(
            id=0x020B,
            type=t.Single,
            access="rwp",
            manufacturer_code=XIAOMI_MFG_CODE,
        )

        child_lock = ZCLAttributeDef(
            id=0x0285,
            type=t.Bool,
            access="rwp",
            manufacturer_code=XIAOMI_MFG_CODE,
        )

        multi_click = ZCLAttributeDef(
            id=0x0286,
            type=t.Bool,
            access="rwp",
            manufacturer_code=XIAOMI_MFG_CODE,
        )

        flip_indicator_light = ZCLAttributeDef(
            id=0x00F0,
            type=t.Bool,
            access="rwp",
            manufacturer_code=XIAOMI_MFG_CODE,
        )


(
    QuirkBuilder(LUMI, "lumi.plug.aeu002")
    .applies_to("Aqara", "lumi.plug.aeu002")
    .replaces(AqaraPlugH2Cluster, endpoint_id=1)
    .replaces(AqaraPlugH2Cluster, endpoint_id=2)
    .replaces(AqaraPlugH2Cluster, endpoint_id=3)
    .replaces(MultistateInputCluster, endpoint_id=1)
    .replaces(MultistateInputCluster, endpoint_id=2)
    # Hide the raw MultistateInput sensors; the buttons are exposed via events.
    .prevent_default_entity_creation(
        endpoint_id=1, cluster_id=MultistateInput.cluster_id
    )
    .prevent_default_entity_creation(
        endpoint_id=2, cluster_id=MultistateInput.cluster_id
    )
    .switch(
        AqaraPlugH2Cluster.AttributeDefs.child_lock.name,
        AqaraPlugH2Cluster.cluster_id,
        endpoint_id=1,
        translation_key="child_lock_socket_1",
        fallback_name="Socket 1 child lock",
    )
    .switch(
        AqaraPlugH2Cluster.AttributeDefs.child_lock.name,
        AqaraPlugH2Cluster.cluster_id,
        endpoint_id=2,
        translation_key="child_lock_socket_2",
        fallback_name="Socket 2 child lock",
    )
    .switch(
        AqaraPlugH2Cluster.AttributeDefs.multi_click.name,
        AqaraPlugH2Cluster.cluster_id,
        endpoint_id=1,
        translation_key="multi_click_socket_1",
        fallback_name="Socket 1 multi-click mode",
    )
    .switch(
        AqaraPlugH2Cluster.AttributeDefs.multi_click.name,
        AqaraPlugH2Cluster.cluster_id,
        endpoint_id=2,
        translation_key="multi_click_socket_2",
        fallback_name="Socket 2 multi-click mode",
    )
    .switch(
        AqaraPlugH2Cluster.AttributeDefs.power_outage_memory.name,
        AqaraPlugH2Cluster.cluster_id,
        translation_key="power_outage_memory",
        fallback_name="Power outage memory",
    )
    .switch(
        AqaraPlugH2Cluster.AttributeDefs.led_indicator.name,
        AqaraPlugH2Cluster.cluster_id,
        translation_key="led_indicator",
        fallback_name="LED indicator",
    )
    .switch(
        AqaraPlugH2Cluster.AttributeDefs.flip_indicator_light.name,
        AqaraPlugH2Cluster.cluster_id,
        translation_key="flip_indicator_light",
        fallback_name="Flip indicator light",
    )
    .number(
        AqaraPlugH2Cluster.AttributeDefs.overload_protection.name,
        AqaraPlugH2Cluster.cluster_id,
        min_value=OVERLOAD_PROTECTION_MIN_WATTS,
        max_value=OVERLOAD_PROTECTION_MAX_WATTS,
        step=1,
        unit=UnitOfPower.WATT,
        device_class=NumberDeviceClass.POWER,
        entity_type=EntityType.CONFIG,
        translation_key="overload_protection",
        fallback_name="Overload protection",
    )
    .device_automation_triggers(
        {
            (SHORT_PRESS, BUTTON_1): {COMMAND: COMMAND_1_SINGLE},
            (DOUBLE_PRESS, BUTTON_1): {COMMAND: COMMAND_1_DOUBLE},
            (LONG_PRESS, BUTTON_1): {COMMAND: COMMAND_1_HOLD},
            (LONG_RELEASE, BUTTON_1): {COMMAND: COMMAND_1_RELEASE},
            (SHORT_PRESS, BUTTON_2): {COMMAND: COMMAND_2_SINGLE},
            (DOUBLE_PRESS, BUTTON_2): {COMMAND: COMMAND_2_DOUBLE},
            (LONG_PRESS, BUTTON_2): {COMMAND: COMMAND_2_HOLD},
            (LONG_RELEASE, BUTTON_2): {COMMAND: COMMAND_2_RELEASE},
        }
    )
    .add_to_registry()
)
