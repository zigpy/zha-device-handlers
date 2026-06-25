"""Shelly WiFi setup cluster support."""

from __future__ import annotations

import zigpy.types as t
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef

from zhaquirks.clusters import CustomCluster
from zhaquirks.shelly import SHELLY_MANUFACTURER_CODE, SHELLY_WIFI_SETUP_CLUSTER_ID

__all__ = [
    "SHELLY_MANUFACTURER_CODE",
    "SHELLY_WIFI_SETUP_CLUSTER_ID",
    "ShellyWiFiSetupCluster",
]


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
