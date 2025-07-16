"""Module for smartthings quirks."""

from zigpy.quirks import CustomCluster
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.security import IasZone

SMART_THINGS = "SmartThings"
MANUFACTURER_SPECIFIC_CLUSTER_ID = 0xFC02  # decimal = 64514


class SmartThingsAccelCluster(CustomCluster):
    """SmartThings Acceleration Cluster."""

    cluster_id = MANUFACTURER_SPECIFIC_CLUSTER_ID
    name = "Smartthings Accelerometer"
    ep_attribute = "accelerometer"
    attributes = {
        0x0000: ("motion_threshold_multiplier", t.uint8_t, True),
        0x0002: ("motion_threshold", t.uint16_t, True),
        0x0010: ("acceleration", t.bitmap8, True),  # acceleration detected
        0x0012: ("x_axis", t.int16s, True),
        0x0013: ("y_axis", t.int16s, True),
        0x0014: ("z_axis", t.int16s, True),
    }


class SmartThingsIasZone(CustomCluster, IasZone):
    """IasZone cluster patched to support SmartThings spec violations."""

    class ClientCommandDefs(IasZone.ClientCommandDefs):
        """Client command definitions."""

        status_change_notification = foundation.ZCLCommandDef(
            id=0x0000,
            schema={
                "zone_status": IasZone.ZoneStatus,
                "extended_status": t.bitmap8,
                # These two should not be optional
                "zone_id?": t.uint8_t,
                "delay?": t.uint16_t,
            },
            is_manufacturer_specific=True,
        )
