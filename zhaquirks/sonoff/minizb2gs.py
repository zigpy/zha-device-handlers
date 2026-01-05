"""Sonoff MINI-ZB2GS - Zigbee Switch."""

from zigpy import types
from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef


class SonoffExternalSwitchTriggerType(types.enum8):
    """extern switch trigger type."""

    Edge_trigger = 0x00
    Pulse_trigger = 0x01
    Normally_on_follow_trigger = 0x02
    Normally_off_follow_trigger = 0x82


class SonoffDetachRelayMode2Type(types.enum8):
    """Detach Relay Mode 2 type."""
    Detach_none = 0x00
    Detach_relay_l1 = 0x01
    Detach_relay_l2 = 0x02
    Detach_relay_l1_l2 = 0x03


class SonoffCluster(CustomCluster):
    """Custom Sonoff cluster."""

    cluster_id = 0xFC11

    manufacturer_id_override = foundation.ZCLHeader.NO_MANUFACTURER_ID

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        external_trigger_mode = ZCLAttributeDef(
            id=0x0016,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        detach_relay_mode2 = ZCLAttributeDef(
            id=0x0019,
            type=t.bitmap8,
            is_manufacturer_specific=True,
        )
        rf_turbo_mode = ZCLAttributeDef(
            id=0x0012,
            type=t.int16s,
            is_manufacturer_specific=True,
        )


(
    QuirkBuilder("SONOFF", "MINI-ZB2GS")
    .replaces(SonoffCluster, endpoint_id=1)
    .replaces(SonoffCluster, endpoint_id=2)
    .enum(
        SonoffCluster.AttributeDefs.external_trigger_mode.name,
        SonoffExternalSwitchTriggerType,
        SonoffCluster.cluster_id,
        translation_key="external_trigger_mode_l1",
        fallback_name="External trigger mode L1",
        endpoint_id=1,
    )
    .enum(
        SonoffCluster.AttributeDefs.external_trigger_mode.name,
        SonoffExternalSwitchTriggerType,
        SonoffCluster.cluster_id,
        translation_key="external_trigger_mode_l2",
        fallback_name="External trigger mode L2",
        endpoint_id=2,
    )
    .enum(
        SonoffCluster.AttributeDefs.detach_relay_mode2.name,
        SonoffDetachRelayMode2Type,
        SonoffCluster.cluster_id,
        translation_key="detach_relay_mode2_l1",
        fallback_name="Detach relay mode L1",
        endpoint_id=1,
    )
    .switch(
        SonoffCluster.AttributeDefs.rf_turbo_mode.name,
        SonoffCluster.cluster_id,
        off_value=9,
        on_value=20,
        translation_key="rf_turbo_mode",
        fallback_name="RF turbo mode",
        endpoint_id=1,
    )
    .add_to_registry()
)
