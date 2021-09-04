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

    class ZoneState(t.enum8):
        """ZoneState attribute."""

        Not_enrolled = 0x00
        Enrolled = 0x01

    class ZoneType(t.enum_factory(t.uint16_t, "manufacturer_specific")):
        """Zone type enum."""

        Standard_CIE = 0x0000
        Motion_Sensor = 0x000D
        Contact_Switch = 0x0015
        Fire_Sensor = 0x0028
        Water_Sensor = 0x002A
        Carbon_Monoxide_Sensor = 0x002B
        Personal_Emergency_Device = 0x002C
        Vibration_Movement_Sensor = 0x002D
        Remote_Control = 0x010F
        Key_Fob = 0x0115
        Key_Pad = 0x021D
        Standard_Warning_Device = 0x0225
        Glass_Break_Sensor = 0x0226
        Security_Repeater = 0x0229
        Invalid_Zone_Type = 0xFFFF

    cluster_id = 0x0500
    name = "IAS Zone"
    ep_attribute = "ias_zone"
    attributes = {
        # Zone Information
        0x0000: ("zone_state", ZoneState),
        0x0001: ("zone_type", ZoneType),
        0x0002: ("zone_status", t.uint16_t),
        # Zone Settings
        0x0010: ("cie_addr", t.EUI64),
        0x0011: ("zone_id", t.uint8_t),
    }

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
