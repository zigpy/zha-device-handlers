"""Shelly WiFi setup cluster support."""

from __future__ import annotations

from zigpy.device import ResponseKey
import zigpy.types as t
from zigpy.zcl import ClusterType, foundation
from zigpy.zcl.clusters.general import OnOff
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef

from zhaquirks.builder import EntityType, QuirkBuilder
from zhaquirks.clusters import CustomCluster
from zhaquirks.device import CustomZigpyDevice
from zhaquirks.shelly import SHELLY_MANUFACTURER_CODE

SHELLY_WIFI_SETUP_ENDPOINT_ID = 239
SHELLY_WIFI_SETUP_PROFILE_ID = 0xC001
SHELLY_WIFI_SETUP_CLUSTER_ID = 0xFC02

# Firmware 2.0.0 ("Zigbee: Add inputs support") exposes the physical input of the
# single-channel relays as endpoint 2, an On/Off Switch whose client On/Off
# cluster sends on/off/toggle commands.  ZHA already mirrors those commands into
# the cluster's on_off cache (OnOffClientCacheSync) but creates no entity for
# that device type, so the quirk only declares the entity; caching the commands
# here as well would apply every toggle twice.
#  <SimpleDescriptor endpoint=2 profile=260 device_type=0
#  input_clusters=[7]
#  output_clusters=[3, 4, 5, 6]>
SHELLY_INPUT_ENDPOINT_ID = 2
# The OTA cluster reports firmware 2.0.0 as 0x020000FF.
SHELLY_INPUTS_FIRMWARE_VERSION = 0x02000000


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


shelly_relay_base = (
    QuirkBuilder("Shelly", "1PM")
    .applies_to("Shelly", "Mini1PM")
    .applies_to("Shelly", "Mini1")
    .device_class(ShellyCustomProfileDevice)
    .replaces(ShellyWiFiSetupCluster, endpoint_id=SHELLY_WIFI_SETUP_ENDPOINT_ID)
)

(
    # Firmware before 2.0.0 has no input endpoint
    shelly_relay_base.clone(omit_man_model_data=False)
    .firmware_version_filter(
        max_version=SHELLY_INPUTS_FIRMWARE_VERSION, allow_missing=False
    )
    .add_to_registry()
)

(
    # Firmware 2.0.0 and newer, or a device that has not reported its version yet
    shelly_relay_base.clone(omit_man_model_data=False)
    .firmware_version_filter(min_version=SHELLY_INPUTS_FIRMWARE_VERSION)
    .binary_sensor(
        attribute_name=OnOff.AttributeDefs.on_off.name,
        cluster_id=OnOff.cluster_id,
        endpoint_id=SHELLY_INPUT_ENDPOINT_ID,
        cluster_type=ClusterType.Client,
        entity_type=EntityType.STANDARD,
        translation_key="input",
        fallback_name="Input",
    )
    .add_to_registry()
)

(
    QuirkBuilder("Shelly", "2PM")
    .applies_to("Shelly", "EM Mini")
    .device_class(ShellyCustomProfileDevice)
    .replaces(ShellyWiFiSetupCluster, endpoint_id=SHELLY_WIFI_SETUP_ENDPOINT_ID)
    .add_to_registry()
)
