"""Quirk for Namron 8-button Zigbee Switch 4512772.

Custom ZHA quirk for exposing all button events for the Namron 4512772
8-button Zigbee switch as device triggers for use in Home Assistant.
"""

from zigpy.quirks import CustomDevice

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)


class Namron4512772(CustomDevice):
    """Custom device handler for Namron 4512772 8-button Zigbee switch."""

    signature = {
        "manufacturer": "NAMRON AS",
        "model": "4512772",
        "node_desc": {
            "logical_type": 0,
            "complex_descriptor_available": 0,
            "user_descriptor_available": 0,
            "aps_flags": 0,
            "frequency_band": 8,
            "mac_capability_flags": 132,
            "manufacturer_code": 4447,
            "maximum_buffer_size": 82,
            "maximum_incoming_transfer_size": 82,
            "server_mask": 11264,
            "maximum_outgoing_transfer_size": 82,
            "descriptor_capability_field": 0,
        },
        "skip_configuration": False,
        MODELS_INFO: [("NAMRON AS", "4512772")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: 0x0104,
                DEVICE_TYPE: 0x0001,
                INPUT_CLUSTERS: [
                    0x0000,  # Basic
                    0x0001,  # PowerConfiguration (battery)
                    0x0003,  # Identify
                    0x0B05,  # Diagnostic
                    0x1000,  # LightLink
                ],
                OUTPUT_CLUSTERS: [
                    0x0003,  # Identify
                    0x0004,  # Groups
                    0x0005,  # Scenes
                    0x0006,  # OnOff
                    0x0008,  # LevelControl
                    0x0019,  # OTA (firmware)
                    0x0300,  # ColorControl
                    0x1000,  # LightLink
                ],
            },
            2: {
                PROFILE_ID: 0x0104,
                DEVICE_TYPE: 0x0001,
                INPUT_CLUSTERS: [0x0000, 0x0001, 0x0003, 0x0B05, 0x1000],
                OUTPUT_CLUSTERS: [
                    0x0003,
                    0x0004,
                    0x0005,
                    0x0006,
                    0x0008,
                    0x0019,
                    0x0300,
                    0x1000,
                ],
            },
            3: {
                PROFILE_ID: 0x0104,
                DEVICE_TYPE: 0x0001,
                INPUT_CLUSTERS: [0x0000, 0x0001, 0x0003, 0x0B05, 0x1000],
                OUTPUT_CLUSTERS: [
                    0x0003,
                    0x0004,
                    0x0005,
                    0x0006,
                    0x0008,
                    0x0019,
                    0x0300,
                    0x1000,
                ],
            },
            4: {
                PROFILE_ID: 0x0104,
                DEVICE_TYPE: 0x0001,
                INPUT_CLUSTERS: [0x0000, 0x0001, 0x0003, 0x0B05, 0x1000],
                OUTPUT_CLUSTERS: [
                    0x0003,
                    0x0004,
                    0x0005,
                    0x0006,
                    0x0008,
                    0x0019,
                    0x0300,
                    0x1000,
                ],
            },
        },
    }

    replacement = {
        MODELS_INFO: [("NAMRON AS", "4512772")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: 0x0104,
                DEVICE_TYPE: 0x0001,
                INPUT_CLUSTERS: [
                    0x0000,  # Basic
                    0x0001,  # PowerConfiguration (battery, only here!)
                    0x0003,  # Identify
                    0x0B05,  # Diagnostic
                    0x1000,  # LightLink
                ],
                OUTPUT_CLUSTERS: [
                    0x0003,  # Identify
                    0x0004,  # Groups
                    0x0005,  # Scenes
                    0x0006,  # OnOff
                    0x0008,  # LevelControl
                    0x0019,  # OTA (firmware, only here!)
                    0x0300,  # ColorControl
                    0x1000,  # LightLink
                ],
            },
            2: {
                PROFILE_ID: 0x0104,
                DEVICE_TYPE: 0x0001,
                INPUT_CLUSTERS: [0x0000, 0x0003, 0x0B05, 0x1000],
                OUTPUT_CLUSTERS: [
                    0x0003,
                    0x0004,
                    0x0005,
                    0x0006,
                    0x0008,
                    0x0300,
                    0x1000,
                ],
            },
            3: {
                PROFILE_ID: 0x0104,
                DEVICE_TYPE: 0x0001,
                INPUT_CLUSTERS: [0x0000, 0x0003, 0x0B05, 0x1000],
                OUTPUT_CLUSTERS: [
                    0x0003,
                    0x0004,
                    0x0005,
                    0x0006,
                    0x0008,
                    0x0300,
                    0x1000,
                ],
            },
            4: {
                PROFILE_ID: 0x0104,
                DEVICE_TYPE: 0x0001,
                INPUT_CLUSTERS: [0x0000, 0x0003, 0x0B05, 0x1000],
                OUTPUT_CLUSTERS: [
                    0x0003,
                    0x0004,
                    0x0005,
                    0x0006,
                    0x0008,
                    0x0300,
                    0x1000,
                ],
            },
        },
    }

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
