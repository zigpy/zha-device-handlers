"""Module for smartthings quirks."""

from zigpy.quirks import CustomCluster
import zigpy.types as t
from zigpy.zcl.clusters.security import IasZone
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef, ZCLCommandDef

SMART_THINGS = "SmartThings"
MANUFACTURER_SPECIFIC_CLUSTER_ID = 0xFC02  # decimal = 64514


class SmartThingsAccelCluster(CustomCluster):
    """SmartThings Acceleration Cluster."""

    cluster_id = MANUFACTURER_SPECIFIC_CLUSTER_ID
    name = "Smartthings Accelerometer"
    ep_attribute = "accelerometer"

    class AttributeDefs(BaseAttributeDefs):
        """Cluster attributes."""

        motion_threshold_multiplier = ZCLAttributeDef(
            id=0x0000, type=t.uint8_t, is_manufacturer_specific=True
        )
        motion_threshold = ZCLAttributeDef(
            id=0x0002, type=t.uint16_t, is_manufacturer_specific=True
        )
        acceleration = ZCLAttributeDef(
            id=0x0010, type=t.bitmap8, is_manufacturer_specific=True
        )  # acceleration detected
        x_axis = ZCLAttributeDef(
            id=0x0012, type=t.int16s, is_manufacturer_specific=True
        )
        y_axis = ZCLAttributeDef(
            id=0x0013, type=t.int16s, is_manufacturer_specific=True
        )
        z_axis = ZCLAttributeDef(
            id=0x0014, type=t.int16s, is_manufacturer_specific=True
        )


class SmartThingsIasZone(CustomCluster, IasZone):
    """IasZone cluster patched to support SmartThings spec violations."""

    class ClientCommandDefs(IasZone.ClientCommandDefs):
        """Client command definitions."""

        status_change_notification = ZCLCommandDef(
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
