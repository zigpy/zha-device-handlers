"""Sonoff ZBMINIR2 - Zigbee Switch."""

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import EntityType, QuirkBuilder
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef


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
        detach_relay = ZCLAttributeDef(
            id=0x0017,
            type=t.Bool,
            is_manufacturer_specific=True,
        )
        work_mode = ZCLAttributeDef(
            id=0x0018,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )


class SonoffExternalSwitchTriggerType(t.enum8):
    """extern switch trigger type."""

    Edge_trigger = 0x00
    Pulse_trigger = 0x01
    Normally_off_follow_trigger = 0x02
    Normally_on_follow_trigger = 0x82


zbm_1c_quirk = (
    QuirkBuilder("SONOFF", "ZBM5-1C-80/86")
    .applies_to("SONOFF", "ZBM5-1C-120")
    .adds(SonoffCluster, endpoint_id=1)
    .sensor(
        SonoffCluster.AttributeDefs.work_mode.name,
        SonoffCluster.cluster_id,
        translation_key="work_mode",
        fallback_name="Work mode",
        entity_type=EntityType.DIAGNOSTIC,
        initially_disabled=True,
    )
    .enum(
        SonoffCluster.AttributeDefs.external_trigger_mode.name,
        SonoffExternalSwitchTriggerType,
        SonoffCluster.cluster_id,
        translation_key="external_trigger_mode",
        fallback_name="External trigger mode",
        endpoint_id=1,
        initially_disabled=True,
    )
    .switch(
        SonoffCluster.AttributeDefs.detach_relay.name,
        SonoffCluster.cluster_id,
        off_value=0,
        on_value=1,
        translation_key="detach_relay",
        fallback_name="Detach relay",
        endpoint_id=1,
        initially_disabled=True,
    )
)
zbm_1c_quirk.add_to_registry()

zbm_2c_quirk = (
    zbm_1c_quirk.clone()
    .applies_to("SONOFF", "ZBM5-2C-80/86")
    .applies_to("SONOFF", "ZBM5-2C-120")
    .adds(SonoffCluster, endpoint_id=2)
    .enum(
        SonoffCluster.AttributeDefs.external_trigger_mode.name,
        SonoffExternalSwitchTriggerType,
        SonoffCluster.cluster_id,
        translation_key="external_trigger_mode",
        fallback_name="External trigger mode",
        endpoint_id=2,
        initially_disabled=True,
    )
    .switch(
        SonoffCluster.AttributeDefs.detach_relay.name,
        SonoffCluster.cluster_id,
        off_value=0,
        on_value=1,
        translation_key="detach_relay",
        fallback_name="Detach relay",
        endpoint_id=2,
        initially_disabled=True,
    )
)
zbm_2c_quirk.add_to_registry()

zbm_3c_quirk = (
    zbm_1c_quirk.clone()
    .applies_to("SONOFF", "ZBM5-3C-80/86")
    .applies_to("SONOFF", "ZBM5-3C-120")
    .adds(SonoffCluster, endpoint_id=3)
    .enum(
        SonoffCluster.AttributeDefs.external_trigger_mode.name,
        SonoffExternalSwitchTriggerType,
        SonoffCluster.cluster_id,
        translation_key="external_trigger_mode",
        fallback_name="External trigger mode",
        endpoint_id=3,
        initially_disabled=True,
    )
    .switch(
        SonoffCluster.AttributeDefs.detach_relay.name,
        SonoffCluster.cluster_id,
        off_value=0,
        on_value=1,
        translation_key="detach_relay",
        fallback_name="Detach relay",
        endpoint_id=3,
        initially_disabled=True,
    )
)
zbm_3c_quirk.add_to_registry()
