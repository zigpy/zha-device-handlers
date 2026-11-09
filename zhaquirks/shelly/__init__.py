"""Module for Shelly devices."""

from __future__ import annotations

from zigpy import types
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef

from zhaquirks.clusters import CustomCluster

SHELLY_MANUFACTURER_CODE = 0x1490


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
