"""Quirks for Develco Products A/S."""

from typing import Final

from zigpy.quirks import CustomCluster
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.security import IasZone, ZoneStatus

from zhaquirks import PowerConfigurationCluster

FRIENT = "frient A/S"
DEVELCO = "Develco Products A/S"


class DevelcoPowerConfiguration(PowerConfigurationCluster):
    """Common use power configuration cluster."""

    MIN_VOLTS = 2.6  # old 2.1
    MAX_VOLTS = 3.0  # old 3.2


class DevelcoIasZone(CustomCluster, IasZone):
    """IAS Zone, patched to fix a bug with the status change notification command."""

    class ClientCommandDefs(IasZone.ClientCommandDefs):
        """IAS Zone command definitions."""

        status_change_notification: Final = foundation.ZCLCommandDef(
            id=0x00,
            schema={
                "zone_status": ZoneStatus,
                "extended_status": t.bitmap8,
                # These two should not be optional
                "zone_id?": t.uint8_t,
                "delay?": t.uint16_t,
            },
            direction=foundation.Direction.Client_to_Server,
        )
