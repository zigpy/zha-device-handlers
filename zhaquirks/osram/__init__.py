"""Osram quirks elements."""

from zigpy.quirks import CustomCluster
from zigpy.zcl.foundation import BaseCommandDefs, ZCLCommandDef

OSRAM = "OSRAM"


class OsramLightCluster(CustomCluster):
    """OsramLightCluster."""

    cluster_id = 0xFC0F
    ep_attribute = "osram_light"
    name = "OsramLight"

    class ServerCommandDefs(BaseCommandDefs):
        """Osram light cluster server command definitions."""

        save_defaults = ZCLCommandDef(
            id=0x0001, schema={}, is_manufacturer_specific=True
        )
