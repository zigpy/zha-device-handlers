from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
from zigpy.zcl.clusters.general import (
    Basic,
    PowerConfiguration,
    Identify,
    Groups,
    Scenes,
    OnOff,
    LevelControl,
)
from zigpy.zcl.clusters.lighting import Color
from zigpy.zcl.clusters.general import Ota
from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)

EP = 1
CLUSTER_ONOFF = 6
CLUSTER_LEVEL = 8
CLUSTER_SCENES = 5
CLUSTER_COLOR_TEMP = 768


class PaulmannHomeRemote(CustomDevice):
    """Quirk for Paulmann 501.41 Zigbee Smart Home Remote with 7 buttons.

    Provides device automation triggers for brightness, color temp, scenes, and power.
    """

    signature = {
        "model": None,
        "manufacturer": None,
        "endpoints": {
            EP: {
                PROFILE_ID: 0x0104,
                DEVICE_TYPE: 0x0105,
                INPUT_CLUSTERS: [0x0000, 0x0001, 0x0003],
                OUTPUT_CLUSTERS: [
                    0x0003,
                    0x0004,
                    0x0005,
                    CLUSTER_ONOFF,
                    CLUSTER_LEVEL,
                    0x0019,
                    CLUSTER_COLOR_TEMP,
                    0x1000,
                ],
            }
        },
    }

    replacement = signature

    device_automation_triggers = {
        # Power Button (Only toggles on/off as command, not useful for automation)
        ("short_press", "Power Button"): {
            "cluster_id": CLUSTER_ONOFF,
            "endpoint_id": EP,
        },
        # Brightness Up (Plus)
        ("short_press", "Plus Button"): {
            "command": "step_with_on_off",
            "cluster_id": CLUSTER_LEVEL,
            "endpoint_id": EP,
            "args": [0, 26, 2],
        },
        ("long_press", "Plus Button"): {
            "command": "move_with_on_off",
            "cluster_id": CLUSTER_LEVEL,
            "endpoint_id": EP,
            "args": [0, 50],
        },
        # Brightness Down (Minus)
        ("short_press", "Minus Button"): {
            "command": "step",
            "cluster_id": CLUSTER_LEVEL,
            "endpoint_id": EP,
            "args": [1, 26, 2],
        },
        ("long_press", "Minus Button"): {
            "command": "move",
            "cluster_id": CLUSTER_LEVEL,
            "endpoint_id": EP,
            "args": [1, 50],
        },
        # Color Temp: Warmer (Fire)
        ("short_press", "Fire Button"): {
            "command": "step_color_temp",
            "cluster_id": CLUSTER_COLOR_TEMP,
            "endpoint_id": EP,
            "args": [1, 30, 2, 0, 0, 0, 0],
        },
        ("long_press", "Fire Button"): {
            "command": "move_color_temp",
            "cluster_id": CLUSTER_COLOR_TEMP,
            "endpoint_id": EP,
            "args": [1, 60, 0, 0, 0, 0],
        },
        # Color Temp: Cooler (Ice)
        ("short_press", "Ice Button"): {
            "command": "step_color_temp",
            "cluster_id": CLUSTER_COLOR_TEMP,
            "endpoint_id": EP,
            "args": [3, 30, 2, 0, 0, 0, 0],
        },
        ("long_press", "Ice Button"): {
            "command": "move_color_temp",
            "cluster_id": CLUSTER_COLOR_TEMP,
            "endpoint_id": EP,
            "args": [3, 60, 0, 0, 0, 0],
        },
        # Scene buttons (Events distinguished by arguments)
        ("short_press", "S1 Button"): {
            "command": "recall",
            "cluster_id": CLUSTER_SCENES,
            "endpoint_id": EP,
            "args": [0, 1, 2],
        },
        ("long_press", "S1 Button"): {
            "command": "store",
            "cluster_id": CLUSTER_SCENES,
            "endpoint_id": EP,
            "args": [0, 1],
        },
        ("short_press", "S2 Button"): {
            "command": "recall",
            "cluster_id": CLUSTER_SCENES,
            "endpoint_id": EP,
            "args": [0, 2, 2],
        },
        ("long_press", "S2 Button"): {
            "command": "store",
            "cluster_id": CLUSTER_SCENES,
            "endpoint_id": EP,
            "args": [0, 2],
        },
    }
