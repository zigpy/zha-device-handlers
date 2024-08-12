"""Device handler for IKEA of Sweden TRADFRI remote control."""

from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl import ClusterType

from zhaquirks.const import (
    CLUSTER_ID,
    COMMAND,
    COMMAND_HOLD,
    COMMAND_MOVE,
    COMMAND_MOVE_ON_OFF,
    COMMAND_OFF,
    COMMAND_ON,
    COMMAND_PRESS,
    COMMAND_STOP,
    COMMAND_STOP_ON_OFF,
    DIM_DOWN,
    DIM_UP,
    ENDPOINT_ID,
    LEFT,
    LONG_PRESS,
    LONG_RELEASE,
    PARAMS,
    RIGHT,
    SHORT_PRESS,
    TURN_OFF,
    TURN_ON,
)
from zhaquirks.ikea import IKEA, DoublingPowerConfig2AAACluster, ScenesCluster

(
    QuirkBuilder(IKEA, "Remote Control N2")
    .replaces(DoublingPowerConfig2AAACluster)  # will only double for old firmware
    .replaces(ScenesCluster, cluster_type=ClusterType.Client)
    .device_automation_triggers(
        {
            (SHORT_PRESS, TURN_ON): {
                COMMAND: COMMAND_ON,
                CLUSTER_ID: 6,
                ENDPOINT_ID: 1,
            },
            (LONG_PRESS, DIM_UP): {
                COMMAND: COMMAND_MOVE_ON_OFF,
                CLUSTER_ID: 8,
                ENDPOINT_ID: 1,
                PARAMS: {"move_mode": 0},
            },
            (LONG_RELEASE, DIM_UP): {
                COMMAND: COMMAND_STOP_ON_OFF,
                CLUSTER_ID: 8,
                ENDPOINT_ID: 1,
            },
            (SHORT_PRESS, TURN_OFF): {
                COMMAND: COMMAND_OFF,
                CLUSTER_ID: 6,
                ENDPOINT_ID: 1,
            },
            (LONG_PRESS, DIM_DOWN): {
                COMMAND: COMMAND_MOVE,
                CLUSTER_ID: 8,
                ENDPOINT_ID: 1,
                PARAMS: {"move_mode": 1},
            },
            (LONG_RELEASE, DIM_DOWN): {
                COMMAND: COMMAND_STOP,
                CLUSTER_ID: 8,
                ENDPOINT_ID: 1,
            },
            (SHORT_PRESS, LEFT): {
                COMMAND: COMMAND_PRESS,
                CLUSTER_ID: 5,
                ENDPOINT_ID: 1,
                PARAMS: {
                    "param1": 257,
                    "param2": 13,
                    "param3": 0,
                },
            },
            (LONG_PRESS, LEFT): {
                COMMAND: COMMAND_HOLD,
                CLUSTER_ID: 5,
                ENDPOINT_ID: 1,
                PARAMS: {
                    "param1": 3329,
                    "param2": 0,
                },
            },
            (SHORT_PRESS, RIGHT): {
                COMMAND: COMMAND_PRESS,
                CLUSTER_ID: 5,
                ENDPOINT_ID: 1,
                PARAMS: {
                    "param1": 256,
                    "param2": 13,
                    "param3": 0,
                },
            },
            (LONG_PRESS, RIGHT): {
                COMMAND: COMMAND_HOLD,
                CLUSTER_ID: 5,
                ENDPOINT_ID: 1,
                PARAMS: {
                    "param1": 3328,
                    "param2": 0,
                },
            },
        }
    )
    .add_to_registry()
)
