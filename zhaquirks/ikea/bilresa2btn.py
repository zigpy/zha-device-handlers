"""IKEA Bilresa 2 button remote control."""

from zigpy.quirks.v2 import QuirkBuilder

from zhaquirks.ikea import IKEA

from zhaquirks.const import (
    CLUSTER_ID,
    COMMAND,
    COMMAND_MOVE,
    COMMAND_MOVE_ON_OFF,
    COMMAND_OFF,
    COMMAND_ON,
    COMMAND_STOP,
    COMMAND_STOP_ON_OFF,
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

(
    QuirkBuilder(IKEA, "09B9")
    .device_automation_triggers(
        {
            (SHORT_PRESS, TURN_ON): {COMMAND: COMMAND_ON, CLUSTER_ID: 6, ENDPOINT_ID: 1},
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
            (SHORT_PRESS, TURN_OFF): {COMMAND: COMMAND_OFF, CLUSTER_ID: 6, ENDPOINT_ID: 1},
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
        } 
    )
    .add_to_registry()
)
