"""Sonoff MINI-ZB2GS - Zigbee Switch."""

from zigpy import types
from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
import zigpy.types as t
from zigpy.zcl.foundation import BaseAttributeDefs, DataTypeId, ZCLAttributeDef


class SonoffExternalSwitchTriggerType(types.enum8):
    """External switch trigger type."""

    Edge_trigger = 0x00
    Pulse_trigger = 0x01
    Normally_off_follow_trigger = 0x02
    Normally_on_follow_trigger = 0x82


class SonoffDetachRelayType(types.enum8):
    """Detach relay type."""

    All_channels_disabled = 0x00
    CH1_enabled = 0x01
    CH2_enabled = 0x02
    All_channels_enabled = 0x03


class SonoffCluster(CustomCluster):
    """Custom Sonoff cluster."""

    cluster_id = 0xFC11

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        external_trigger_mode = ZCLAttributeDef(
            id=0x0016,
            type=SonoffExternalSwitchTriggerType,
            zcl_type=DataTypeId.uint8,
            manufacturer_code=None,
        )
        detach_relay = ZCLAttributeDef(
            id=0x0019,
            type=SonoffDetachRelayType,
            zcl_type=DataTypeId.map8,
            manufacturer_code=None,
        )
        turbo_mode = ZCLAttributeDef(
            id=0x0012,
            type=t.int16s,
            manufacturer_code=None,
        )
        network_led = ZCLAttributeDef(
            id=0x0001,
            type=t.Bool,
            manufacturer_code=None,
        )


(
    QuirkBuilder("SONOFF", "MINI-ZB2GS")
    .replaces(SonoffCluster, endpoint_id=1)
    .replaces(SonoffCluster, endpoint_id=2)
    .enum(
        SonoffCluster.AttributeDefs.external_trigger_mode.name,
        SonoffExternalSwitchTriggerType,
        SonoffCluster.cluster_id,
        endpoint_id=1,
        translation_key="external_trigger_mode",
        fallback_name="External trigger mode",
    )
    .enum(
        SonoffCluster.AttributeDefs.detach_relay.name,
        SonoffDetachRelayType,
        SonoffCluster.cluster_id,
        endpoint_id=1,
        translation_key="detach_relay",
        fallback_name="Detach relay",
    )
    .enum(
        SonoffCluster.AttributeDefs.external_trigger_mode.name,
        SonoffExternalSwitchTriggerType,
        SonoffCluster.cluster_id,
        endpoint_id=2,
        translation_key="external_trigger_mode",
        fallback_name="External trigger mode",
    )
    .switch(
        SonoffCluster.AttributeDefs.turbo_mode.name,
        SonoffCluster.cluster_id,
        endpoint_id=1,
        off_value=9,
        on_value=20,
        translation_key="turbo_mode",
        fallback_name="Turbo mode",
    )
    .switch(
        SonoffCluster.AttributeDefs.network_led.name,
        SonoffCluster.cluster_id,
        endpoint_id=1,
        translation_key="network_led",
        fallback_name="Network LED",
    )
    .add_to_registry()
)
