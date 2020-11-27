"""Module for smartthings quirks."""

from zigpy.quirks import CustomCluster
import zigpy.types as t
from zigpy.zcl.clusters.security import IasZone

SMART_THINGS = "SmartThings"
MANUFACTURER_SPECIFIC_CLUSTER_ID = 0xFC02  # decimal = 64514


class SmartThingsAccelCluster(CustomCluster):
    """SmartThings Acceleration Cluster."""

    cluster_id = MANUFACTURER_SPECIFIC_CLUSTER_ID
    name = "Smartthings Accelerometer"
    ep_attribute = "accelerometer"
    manufacturer_attributes = {
        0x0000: ("motion_threshold_multiplier", t.uint8_t),
        0x0002: ("motion_threshold", t.uint16_t),
        0x0010: ("acceleration", t.bitmap8),  # acceleration detected
        0x0012: ("x_axis", t.int16s),
        0x0013: ("y_axis", t.int16s),
        0x0014: ("z_axis", t.int16s),
    }


class SmartThingsIasZone(CustomCluster, IasZone):
    """IasZone cluster patched to support SmartThings spec violations."""

    manufacturer_client_commands = {
        0x0000: (
            "status_change_notification",
            (
                IasZone.ZoneStatus,
                t.bitmap8,
                # SmartThings never sends these two
                t.Optional(t.uint8_t),
                t.Optional(t.uint16_t),
            ),
            False,
        )
    }
