"""Osram quirks elements."""
from zigpy.quirks import CustomCluster
from zigpy.zcl.foundation import ZCLCommandDef

OSRAM = "OSRAM"


class OsramLightCluster(CustomCluster):
    """OsramLightCluster."""

    cluster_id = 0xFC0F
    ep_attribute = "osram_light"
    name = "OsramLight"
    server_commands = {
        0x0001: ZCLCommandDef(
            "save_defaults", {}, False, is_manufacturer_specific=True
        ),
    }
