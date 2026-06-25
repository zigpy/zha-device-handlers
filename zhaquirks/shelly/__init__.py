"""Module for Shelly devices."""

from __future__ import annotations

from zigpy import types
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef

from zhaquirks.clusters import CustomCluster

SHELLY_MANUFACTURER_CODE = 0x1490
SHELLY_CUSTOM_ENDPOINT_ID = 239
SHELLY_CUSTOM_PROFILE_ID = 0xC001
SHELLY_RPC_CLUSTER_ID = 0xFC01
SHELLY_WIFI_SETUP_CLUSTER_ID = 0xFC02
SHELLY_INPUT_REFRESH_MIN_INTERVAL = 5
SHELLY_INPUT_REFRESH_TIMEOUT = 20
SHELLY_RPC_DATA_CHUNK_SIZE = 40
SHELLY_RPC_REPORTED_RESPONSE_GRACE_PERIOD = 1
SHELLY_RPC_RESPONSE_TIMEOUT = 15
SHELLY_RPC_RESPONSE_POLL_INTERVAL = 0.25
SHELLY_RPC_SOURCE = "zha"


class LightLevel(types.enum8):
    """Shelly coarse light level values."""

    dark = 0x00
    twilight = 0x01
    bright = 0x02


class ShellyLightLevelCluster(CustomCluster):
    """Shelly manufacturer-specific cluster exposing a coarse light level."""

    cluster_id = 0xFC21
    name = "Shelly Light Level"
    ep_attribute = "shelly_light_level"

    class AttributeDefs(BaseAttributeDefs):
        """Light level cluster attribute definitions."""

        light_level = ZCLAttributeDef(
            id=0x0000,
            type=types.uint8_t,
            access="rp",
            manufacturer_code=SHELLY_MANUFACTURER_CODE,
        )
        dark_threshold = ZCLAttributeDef(
            id=0x0001,
            type=types.uint24_t,
            access="rw",
            manufacturer_code=SHELLY_MANUFACTURER_CODE,
        )
        bright_threshold = ZCLAttributeDef(
            id=0x0002,
            type=types.uint24_t,
            access="rw",
            manufacturer_code=SHELLY_MANUFACTURER_CODE,
        )
