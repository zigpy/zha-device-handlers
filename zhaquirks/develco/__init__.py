"""Quirks for Develco Products A/S."""

from zigpy import types as t
from zigpy.quirks import CustomCluster
from zigpy.zcl import foundation
from zigpy.zcl.clusters.security import IasZone

from zhaquirks import PowerConfigurationCluster

DEVELCO = "Develco Products A/S"


class DevelcoPowerConfiguration(PowerConfigurationCluster):
    """Common use power configuration cluster."""

    MIN_VOLTS = 2.6  # old 2.1
    MAX_VOLTS = 3.0  # old 3.2


class DevelcoIasZone(CustomCluster, IasZone):
    """Custom IasZone for Develco."""

    client_commands = {}
    server_commands = {
        0x00: foundation.ZCLCommandDef(
            "status_change_notification", {"zone_status": IasZone.ZoneStatus}, False
        ),
        # XXX: In the IasZone *client* commands, this is called just `enroll`
        0x01: foundation.ZCLCommandDef(
            "zone_enroll_request",
            {"zone_type": IasZone.ZoneType, "manufacturer_code": t.uint16_t},
            False,
        ),
    }
