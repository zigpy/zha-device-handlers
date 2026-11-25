"""Shelly WiFi setup cluster support."""

from __future__ import annotations

import re

from zigpy.device import ResponseKey, ZigbeeDevice
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import Basic
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef

from zhaquirks.builder import QuirkBuilder
from zhaquirks.clusters import CustomCluster
from zhaquirks.device import CustomZigpyDevice
from zhaquirks.shelly import SHELLY_MANUFACTURER_CODE

SHELLY_WIFI_SETUP_ENDPOINT_ID = 239
SHELLY_WIFI_SETUP_PROFILE_ID = 0xC001
SHELLY_WIFI_SETUP_CLUSTER_ID = 0xFC02
SHELLY_RELAY_MODELS = ("1PM", "1", "2PM", "Mini1PM", "Mini1", "EM Mini")
SHELLY_ROUTING_ISSUE_MODELS = ("1PM", "2PM", "Mini1PM")
SHELLY_ROUTING_ISSUE_URL = "https://github.com/Koenkk/zigbee2mqtt/issues/32704"
SHELLY_ROUTING_ISSUE_MESSAGE = (
    "Shelly firmware 2.0.x and 2.1.x has a known Zigbee routing issue that can "
    "leave the device reporting telemetry while rejecting commands. Update the "
    f"device when Shelly publishes a fix. See {SHELLY_ROUTING_ISSUE_URL}."
)


def _has_shelly_routing_issue(device: ZigbeeDevice) -> bool:
    """Return whether the device runs a firmware version with the routing issue."""
    try:
        basic_cluster = device.endpoints[1].in_clusters[Basic.cluster_id]
    except KeyError:
        return False

    software_build_id = basic_cluster.get(Basic.AttributeDefs.sw_build_id.id)
    if not isinstance(software_build_id, str):
        return False

    match = re.match(r"^(\d+)\.(\d+)\.(\d+)", software_build_id)
    if match is None:
        return False

    version = tuple(int(component) for component in match.groups())
    return (2, 0, 0) <= version < (2, 2, 0)


def _shelly_wifi_quirk_builder(models: tuple[str, ...]) -> QuirkBuilder:
    """Create a WiFi setup quirk builder for Shelly relay models."""
    builder = QuirkBuilder("Shelly", models[0])
    for model in models[1:]:
        builder.applies_to("Shelly", model)
    return builder.device_class(ShellyCustomProfileDevice).replaces(
        ShellyWiFiSetupCluster, endpoint_id=SHELLY_WIFI_SETUP_ENDPOINT_ID
    )


class ShellyWiFiSetupCluster(CustomCluster):
    """Shelly WiFi setup cluster."""

    cluster_id = SHELLY_WIFI_SETUP_CLUSTER_ID
    name = "Shelly WiFi Setup"
    ep_attribute = "shelly_wifi_setup"

    class AttributeDefs(BaseAttributeDefs):
        """Shelly WiFi setup attribute definitions."""

        status = ZCLAttributeDef(
            id=0x0000,
            type=t.CharacterString,
            access="r",
            manufacturer_code=SHELLY_MANUFACTURER_CODE,
        )
        ip = ZCLAttributeDef(
            id=0x0001,
            type=t.CharacterString,
            access="r",
            manufacturer_code=SHELLY_MANUFACTURER_CODE,
        )
        action = ZCLAttributeDef(
            id=0x0002,
            type=t.uint8_t,
            access="w",
            manufacturer_code=SHELLY_MANUFACTURER_CODE,
        )
        dhcp = ZCLAttributeDef(
            id=0x0003,
            type=t.Bool,
            access="r",
            manufacturer_code=SHELLY_MANUFACTURER_CODE,
        )
        enable = ZCLAttributeDef(
            id=0x0004,
            type=t.Bool,
            access="rw",
            manufacturer_code=SHELLY_MANUFACTURER_CODE,
        )
        ssid = ZCLAttributeDef(
            id=0x0005,
            type=t.CharacterString,
            access="rw",
            manufacturer_code=SHELLY_MANUFACTURER_CODE,
        )
        password = ZCLAttributeDef(
            id=0x0006,
            type=t.CharacterString,
            access="w",
            manufacturer_code=SHELLY_MANUFACTURER_CODE,
        )
        static_ip = ZCLAttributeDef(
            id=0x0007,
            type=t.CharacterString,
            access="rw",
            manufacturer_code=SHELLY_MANUFACTURER_CODE,
        )
        netmask = ZCLAttributeDef(
            id=0x0008,
            type=t.CharacterString,
            access="rw",
            manufacturer_code=SHELLY_MANUFACTURER_CODE,
        )
        gateway = ZCLAttributeDef(
            id=0x0009,
            type=t.CharacterString,
            access="rw",
            manufacturer_code=SHELLY_MANUFACTURER_CODE,
        )
        nameserver = ZCLAttributeDef(
            id=0x000A,
            type=t.CharacterString,
            access="rw",
            manufacturer_code=SHELLY_MANUFACTURER_CODE,
        )


class ShellyCustomProfileDevice(CustomZigpyDevice):
    """Handle Shelly responses sent on their custom endpoint profile."""

    def _parse_packet_header(
        self, packet: t.ZigbeePacket
    ) -> tuple[foundation.ZCLHeader, ResponseKey] | tuple[None, None]:
        """Parse Shelly custom-profile packets as ZCL for normal zigpy matching."""
        if packet.profile_id != SHELLY_WIFI_SETUP_PROFILE_ID:
            return super()._parse_packet_header(packet)

        hdr, _ = foundation.ZCLHeader.deserialize(packet.data.serialize())
        rsp_key = ResponseKey(
            endpoint_id=packet.src_ep,
            cluster_id=packet.cluster_id,
            direction=hdr.frame_control.direction,
            tsn=hdr.tsn,
        )
        return hdr, rsp_key


_shelly_wifi_quirk_builder(SHELLY_RELAY_MODELS).add_to_registry()

(
    _shelly_wifi_quirk_builder(SHELLY_ROUTING_ISSUE_MODELS)
    .filter(_has_shelly_routing_issue)
    .device_alert(level="warning", message=SHELLY_ROUTING_ISSUE_MESSAGE)
    .add_to_registry()
)
