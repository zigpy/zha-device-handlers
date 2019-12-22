"""Module for smartthings quirks."""

import zigpy.types as t
from zigpy.quirks import CustomCluster

SMART_THINGS = "SmartThings"
MANUFACTURER_SPECIFIC_CLUSTER_ID = 0xFC02  # decimal = 64514


class SmartThingsAccelCluster(CustomCluster):
    """SmartThings Acceleration Cluster."""

    cluster_id = MANUFACTURER_SPECIFIC_CLUSTER_ID
    name = "Smartthings Accelerometer"
    ep_attribute = "accelerometer"
    attributes = {
        0x0000: ("motion_threshold_multiplier", t.uint8_t),
        0x0002: ("motion_threshold", t.uint16_t),
        0x0010: ("acceleration", t.bitmap8),  # acceleration detected
        0x0012: ("x_axis", t.int16s),
        0x0013: ("y_axis", t.int16s),
        0x0014: ("z_axis", t.int16s),
    }

    client_commands = {}
    server_commands = {}
