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

    class ZoneStatus(t.uint16_t):
        """ZoneStatus attribute."""

        Alarm_1 = 0x0000
        Battery = 0x0003
        Supervision_reports = 0x0004
        Restore_reports = 0x0005
        Test = 0x0008

    cluster_id = 0x0500
    name = "IAS Zone"
    ep_attribute = "ias_zone"
    attributes = {
        # Zone Information
        0x0000: ("zone_state", IasZone.ZoneState),
        0x0001: ("zone_type", IasZone.ZoneType),
        0x0002: ("zone_status", ZoneStatus),
        # Zone Settings
        0x0010: ("cie_addr", t.EUI64),
        0x0011: ("zone_id", t.uint8_t),
    }
