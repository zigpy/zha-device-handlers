"""IKEA Bilresa 2 button remote control."""

from zigpy.quirks.v2 import QuirkBuilder, CustomDeviceV2
from zigpy.zcl import ClusterType

from zhaquirks.ikea import IKEA, IkeaBilresaLevelControl, ScenesCluster

from zhaquirks.const import (
    CLUSTER_ID,
    COMMAND,
    COMMAND_MOVE,
    COMMAND_OFF,
    COMMAND_ON,
    COMMAND_PRESS,
    DOUBLE_PRESS,
    DIM_DOWN,
    DIM_UP,
    ENDPOINT_ID,
    LONG_PRESS,
    LONG_RELEASE,
    PARAMS,
    SHORT_PRESS,
    TURN_OFF,
    TURN_ON,
)

class IkeaBilresa2ButtonRemote(CustomDeviceV2):
    """Custom device for IKEA Bilresa 2 button remote."""

(
    QuirkBuilder(IKEA, "09B9")
    .replaces(ScenesCluster, cluster_type=ClusterType.Client)
    .replace_cluster_occurrences(IkeaBilresaLevelControl)
    .device_automation_triggers(
        {
            (SHORT_PRESS, TURN_ON): {
                COMMAND: COMMAND_ON, 
                CLUSTER_ID: 6, 
                ENDPOINT_ID: 1
            },
            (LONG_PRESS, DIM_UP): {
                COMMAND: COMMAND_MOVE,
                CLUSTER_ID: 8,
                ENDPOINT_ID: 1,
                PARAMS: {"move_mode": 0},
            },
            (LONG_RELEASE, DIM_UP): {
                COMMAND: "move_up_release",
                CLUSTER_ID: 8,
                ENDPOINT_ID: 1,
            },
            (SHORT_PRESS, TURN_OFF): {
                COMMAND: COMMAND_OFF, 
                CLUSTER_ID: 6, 
                ENDPOINT_ID: 1
            },
            (LONG_PRESS, DIM_DOWN): {
                COMMAND: COMMAND_MOVE,
                CLUSTER_ID: 8,
                ENDPOINT_ID: 1,
                PARAMS: {"move_mode": 1},
            },
            (LONG_RELEASE, DIM_DOWN): {
                COMMAND: "move_down_release",
                CLUSTER_ID: 8,
                ENDPOINT_ID: 1,
            },
            (DOUBLE_PRESS, DIM_UP): {
                COMMAND: COMMAND_PRESS,
                CLUSTER_ID: 5,
                ENDPOINT_ID: 1,
                PARAMS: {
                    "param1": 256,
                    "param2": 13,
                    "param3": 0,
                },
            },
            (DOUBLE_PRESS, DIM_DOWN): {
                COMMAND: COMMAND_PRESS,
                CLUSTER_ID: 5,
                ENDPOINT_ID: 1,
                PARAMS: {
                    "param1": 257,
                    "param2": 13,
                    "param3": 0,
                },
            },
        } 
    )
    .add_to_registry()
)