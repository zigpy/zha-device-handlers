"""Shelly WiFi setup cluster support."""

from __future__ import annotations

from zigpy.profiles import zha
from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import CustomDeviceV2, QuirkBuilder
import zigpy.types as t
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef

SHELLY_MANUFACTURER_CODE = 0x1490
SHELLY_WIFI_SETUP_ENDPOINT_ID = 239
SHELLY_WIFI_SETUP_PROFILE_ID = 0xC001
SHELLY_WIFI_SETUP_DEVICE_TYPE = 0x2001
SHELLY_WIFI_SETUP_CLUSTER_ID = 0xFC02


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


class ShellyCustomProfileDevice(CustomDeviceV2):
    """Handle Shelly responses sent on their custom endpoint profile."""

    def custom_profile_packet_received(self, packet: t.ZigbeePacket) -> None:
        """Treat Shelly's custom profile packets as standard ZCL packets."""
        if packet.profile_id != SHELLY_WIFI_SETUP_PROFILE_ID:
            return super().custom_profile_packet_received(packet)

        self.packet_received(packet.replace(profile_id=zha.PROFILE_ID))


(
    QuirkBuilder("Shelly", "1PM")
    .applies_to("Shelly", "2PM")
    .device_class(ShellyCustomProfileDevice)
    .replaces_endpoint(
        SHELLY_WIFI_SETUP_ENDPOINT_ID,
        profile_id=SHELLY_WIFI_SETUP_PROFILE_ID,
        device_type=SHELLY_WIFI_SETUP_DEVICE_TYPE,
    )
    .replaces(ShellyWiFiSetupCluster, endpoint_id=SHELLY_WIFI_SETUP_ENDPOINT_ID)
    .add_to_registry()
)
