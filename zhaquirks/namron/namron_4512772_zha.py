"""Quirk for Namron 8-button Zigbee Switch 4512772 (v2 interface).

Exposes button events as device triggers for Home Assistant.
"""

from zhaquirks import CustomDevice
from zhaquirks.const import MODELS_INFO

class Namron4512772(CustomDevice):
    """Namron 4512772 8-button Zigbee switch (v2 interface)."""

    MODELS_INFO = [("NAMRON AS", "4512772")]

    device_automation_triggers = {
        # Channel 1
        ("short_press", "channel_1_on"): {
            "command": "on",
            "endpoint_id": 1,
            "cluster_id": 0x0006,
        },
        ("short_press", "channel_1_off"): {
            "command": "off",
            "endpoint_id": 1,
            "cluster_id": 0x0006,
        },
        ("long_hold", "channel_1_on"): {
            "command": "move_with_on_off",
            "endpoint_id": 1,
            "cluster_id": 0x0008,
        },
        ("long_release", "channel_1_on"): {
            "command": "stop_with_on_off",
            "endpoint_id": 1,
            "cluster_id": 0x0008,
        },
        # Channel 2
        ("short_press", "channel_2_on"): {
            "command": "on",
            "endpoint_id": 2,
            "cluster_id": 0x0006,
        },
        ("short_press", "channel_2_off"): {
            "command": "off",
            "endpoint_id": 2,
            "cluster_id": 0x0006,
        },
        ("long_hold", "channel_2_on"): {
            "command": "move_with_on_off",
            "endpoint_id": 2,
            "cluster_id": 0x0008,
        },
        ("long_release", "channel_2_on"): {
            "command": "stop_with_on_off",
            "endpoint_id": 2,
            "cluster_id": 0x0008,
        },
        # Channel 3
        ("short_press", "channel_3_on"): {
            "command": "on",
            "endpoint_id": 3,
            "cluster_id": 0x0006,
        },
        ("short_press", "channel_3_off"): {
            "command": "off",
            "endpoint_id": 3,
            "cluster_id": 0x0006,
        },
        ("long_hold", "channel_3_on"): {
            "command": "move_with_on_off",
            "endpoint_id": 3,
            "cluster_id": 0x0008,
        },
        ("long_release", "channel_3_on"): {
            "command": "stop_with_on_off",
            "endpoint_id": 3,
            "cluster_id": 0x0008,
        },
        # Channel 4
        ("short_press", "channel_4_on"): {
            "command": "on",
            "endpoint_id": 4,
            "cluster_id": 0x0006,
        },
        ("short_press", "channel_4_off"): {
            "command": "off",
            "endpoint_id": 4,
            "cluster_id": 0x0006,
        },
        ("long_hold", "channel_4_on"): {
            "command": "move_with_on_off",
            "endpoint_id": 4,
            "cluster_id": 0x0008,
        },
        ("long_release", "channel_4_on"): {
            "command": "stop_with_on_off",
            "endpoint_id": 4,
            "cluster_id": 0x0008,
        },
    }
