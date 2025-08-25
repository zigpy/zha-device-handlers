"""Ledvance quirks elements."""

from zigpy.quirks import CustomCluster
from zigpy.zcl import foundation
from zigpy.zcl.foundation import BaseCommandDefs

LEDVANCE = "LEDVANCE"


class LedvanceLightCluster(CustomCluster):
    """LedvanceLightCluster."""

    cluster_id = 0xFC01
    ep_attribute = "ledvance_light"
    name = "LedvanceLight"

    class ServerCommandDefs(BaseCommandDefs):
        """Server command definitions."""

        save_defaults = foundation.ZCLCommandDef(
            id=0x0001, schema={}, is_manufacturer_specific=True
        )
