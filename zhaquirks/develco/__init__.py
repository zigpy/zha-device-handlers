"""Quirks for Develco Products A/S."""

from zigpy import types as t
from zigpy.quirks import CustomCluster
from zigpy.zcl.clusters.security import IasZone

from zhaquirks import PowerConfigurationCluster

FRIENT = "frient A/S"
DEVELCO = "Develco Products A/S"


class DevelcoPowerConfiguration(PowerConfigurationCluster):
    """Common use power configuration cluster."""

    MIN_VOLTS = 2.6  # old 2.1
    MAX_VOLTS = 3.0  # old 3.2


class DevelcoIasZone(CustomCluster, IasZone):
    """Custom IasZone for Develco."""

    client_commands = {
        0x0000: (
            "status_change_notification",
            (
                IasZone.ZoneStatus,
                t.Optional(t.bitmap8),
                t.Optional(t.uint8_t),
                t.Optional(t.uint16_t),
            ),
            False,
        ),
        0x0001: ("enroll", (IasZone.ZoneType, t.uint16_t), False),
    }
