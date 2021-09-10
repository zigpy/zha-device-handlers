"""Quirks for Develco Products A/S."""

from zigpy import types as t
from zigpy.quirks import CustomCluster
from zigpy.zcl.clusters.security import IasZone

from zhaquirks import PowerConfigurationCluster

DEVELCO = "Develco Products A/S"


class DevelcoPowerConfiguration(PowerConfigurationCluster):
    """Common use power configuration cluster."""

    MIN_VOLTS = 2.6  # old 2.1
    MAX_VOLTS = 3.0  # old 3.2


class DevelcoIasZone(CustomCluster, IasZone):
    """Custom IasZone for Develco."""

    server_commands = {
        0x0000: ("status_change_notification", (t.uint16_t,), False),
        0x0001: (
            "zone_enroll_request",
            (
                t.enum16,
                t.uint16_t,
            ),
            False,
        ),
    }
