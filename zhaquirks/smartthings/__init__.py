import zigpy.types as t
from zigpy.quirks import CustomDevice, CustomCluster


class SmartThingsAccelCluster(CustomCluster):
    cluster_id = 0xfc02
    name = "Smartthings Accelerometer"
    ep_attribute = 'accelerometer'
    attributes = {
        0x0000: ('motion_threshold_multiplier', t.uint8_t),
        0x0002: ('motion_threshold', t.uint16_t),
        0x0010: ('acceleration', t.bitmap8),  # acceleration detected
        0x0012: ('x_axis', t.int16s),
        0x0013: ('y_axis', t.int16s),
        0x0014: ('z_axis', t.int16s),
    }

    client_commands = {}
    server_commands = {}
