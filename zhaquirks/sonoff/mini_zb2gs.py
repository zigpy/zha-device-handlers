"""Sonoff MINI-ZB2GS and MINI-ZB2GS-L - Zigbee Switches."""

from contextlib import suppress

from zigpy import types
import zigpy.types as t
from zigpy.zcl.clusters.general import OnOff as OnOffBase
from zigpy.zcl.foundation import BaseAttributeDefs, DataTypeId, ZCLAttributeDef

from zhaquirks.builder import QuirkBuilder
from zhaquirks.clusters import CustomCluster
from zhaquirks.const import CLUSTER_ID, COMMAND, ENDPOINT_ID, ZHA_SEND_EVENT

# Attribute Define
RELAY_DETACH_ATTR_ID = 0x0028


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


class RelaySperaKeyAction(types.enum8):
    """Relay detached key action enumeration."""

    Unknown = 0x00
    Single_click = 0x01
    Double_click = 0x02
    Long_press = 0x03
    Follow_on = 0x04
    Follow_off = 0x05


class OnOff(CustomCluster, OnOffBase):
    """Map a `toggle` command received by the gateway into a single-click event."""

    def handle_cluster_request(self, hdr, args, *, dst_addressing=None):
        """Handle cluster request and map toggle command to single-click event."""
        if hdr.command_id == OnOffBase.ServerCommandDefs.toggle.id:
            sonoff_cluster = self.endpoint.in_clusters.get(SonoffCluster.cluster_id)
            if sonoff_cluster is not None:
                sonoff_cluster.update_attribute(
                    RELAY_DETACH_ATTR_ID, RelaySperaKeyAction.Single_click.value
                )
        return super().handle_cluster_request(hdr, args, dst_addressing=dst_addressing)


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
        relay_spera_key_action_event = ZCLAttributeDef(
            id=RELAY_DETACH_ATTR_ID,
            type=RelaySperaKeyAction,
            zcl_type=DataTypeId.uint8,
            manufacturer_code=None,
        )

    def _update_attribute(self, attrid, value):
        if attrid == RELAY_DETACH_ATTR_ID and isinstance(value, int):
            with suppress(ValueError):
                value = RelaySperaKeyAction(value).name

        super()._update_attribute(attrid, value)

        if attrid == RELAY_DETACH_ATTR_ID:
            with suppress(Exception):
                self.listener_event(ZHA_SEND_EVENT, value, {})


zb2gs_l_quirk = (
    QuirkBuilder("SONOFF", "MINI-ZB2GS-L")
    .replaces(SonoffCluster, endpoint_id=1)
    .replaces(SonoffCluster, endpoint_id=2)
    .replace_cluster_occurrences(OnOff)
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
    .device_automation_triggers(
        {
            ("External Switch 1 action", "Single Click"): {
                CLUSTER_ID: SonoffCluster.cluster_id,
                ENDPOINT_ID: 1,
                COMMAND: "Single_click",
            },
            ("External Switch 1 action", "Double Click"): {
                CLUSTER_ID: SonoffCluster.cluster_id,
                ENDPOINT_ID: 1,
                COMMAND: "Double_click",
            },
            ("External Switch 1 action", "Long Press"): {
                CLUSTER_ID: SonoffCluster.cluster_id,
                ENDPOINT_ID: 1,
                COMMAND: "Long_press",
            },
            ("External Switch 1 action", "Follow On"): {
                CLUSTER_ID: SonoffCluster.cluster_id,
                ENDPOINT_ID: 1,
                COMMAND: "Follow_on",
            },
            ("External Switch 1 action", "Follow Off"): {
                CLUSTER_ID: SonoffCluster.cluster_id,
                ENDPOINT_ID: 1,
                COMMAND: "Follow_off",
            },
            ("External Switch 2 action", "Single Click"): {
                CLUSTER_ID: SonoffCluster.cluster_id,
                ENDPOINT_ID: 2,
                COMMAND: "Single_click",
            },
            ("External Switch 2 action", "Double Click"): {
                CLUSTER_ID: SonoffCluster.cluster_id,
                ENDPOINT_ID: 2,
                COMMAND: "Double_click",
            },
            ("External Switch 2 action", "Long Press"): {
                CLUSTER_ID: SonoffCluster.cluster_id,
                ENDPOINT_ID: 2,
                COMMAND: "Long_press",
            },
            ("External Switch 2 action", "Follow On"): {
                CLUSTER_ID: SonoffCluster.cluster_id,
                ENDPOINT_ID: 2,
                COMMAND: "Follow_on",
            },
            ("External Switch 2 action", "Follow Off"): {
                CLUSTER_ID: SonoffCluster.cluster_id,
                ENDPOINT_ID: 2,
                COMMAND: "Follow_off",
            },
        }
    )
)
zb2gs_l_quirk.add_to_registry()

zb2gs_quirk = (
    zb2gs_l_quirk.clone()
    .applies_to("SONOFF", "MINI-ZB2GS")
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
)
zb2gs_quirk.add_to_registry()
