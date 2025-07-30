"""Quirks for Develco Products A/S."""

from zigpy import types as t
from zigpy.quirks import CustomCluster
from zigpy.zcl import foundation
from zigpy.zcl.clusters.security import IasZone
from zigpy.zcl.foundation import BaseCommandDefs

from zhaquirks import PowerConfigurationCluster

FRIENT = "frient A/S"
DEVELCO = "Develco Products A/S"


class DevelcoPowerConfiguration(PowerConfigurationCluster):
    """Common use power configuration cluster."""

    MIN_VOLTS = 2.6  # old 2.1
    MAX_VOLTS = 3.0  # old 3.2


class DevelcoIasZone(CustomCluster, IasZone):
    """Custom IasZone for Develco."""

    class ClientCommandDefs(BaseCommandDefs):
        """Client command definitions."""

        status_change_notification = foundation.ZCLCommandDef(
            id=0x00,
            schema={
                "zone_status": IasZone.ZoneStatus,
                "extended_status?": t.bitmap8,
                "zone_id?": t.uint8_t,
                "delay?": t.uint16_t,
            },
        )
        enroll = foundation.ZCLCommandDef(
            id=0x01,
            schema={"zone_type": IasZone.ZoneType, "manufacturer_code": t.uint16_t},
        )
