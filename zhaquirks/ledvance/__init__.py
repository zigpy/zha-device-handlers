"""Ledvance quirks elements."""
from zigpy.quirks import CustomCluster
from zigpy.zcl import foundation

LEDVANCE = "LEDVANCE"


class LedvanceLightCluster(CustomCluster):
    """LedvanceLightCluster."""

    cluster_id = 0xFC01
    ep_attribute = "ledvance_light"
    name = "LedvanceLight"
    server_commands = {
        0x0001: foundation.ZCLCommandDef(
            "save_defaults", {}, False, is_manufacturer_specific=True
        )
    }
