"""Device handler for CCS-Switch-D0001 remote control."""

from zigpy.quirks.v2 import QuirkBuilder

from zhaquirks.const import (
    ARGS,
    CLUSTER_ID,
    COMMAND,
    COMMAND_MOVE,
    COMMAND_MOVE_ON_OFF,
    COMMAND_RELEASE,
    COMMAND_STEP,
    COMMAND_STEP_ON_OFF,
    COMMAND_TOGGLE,
    DIM_DOWN,
    DIM_UP,
    ENDPOINT_ID,
    LONG_PRESS,
    PARAMS,
    SHORT_PRESS,
    TURN_ON,
)
from zhaquirks.lds import MANUFACTURER

(
    QuirkBuilder(MANUFACTURER, "ZBT-CCTSwitch-D0001")
    .device_automation_triggers(
        {
            (SHORT_PRESS, TURN_ON): {
                COMMAND: COMMAND_TOGGLE,
                CLUSTER_ID: 6,
                ENDPOINT_ID: 1,
            },
            (LONG_PRESS, TURN_ON): {
                COMMAND: COMMAND_RELEASE,
                CLUSTER_ID: 5,
                ENDPOINT_ID: 1,
                ARGS: [],
            },
            (SHORT_PRESS, DIM_UP): {
                COMMAND: COMMAND_STEP_ON_OFF,
                CLUSTER_ID: 8,
                ENDPOINT_ID: 1,
                PARAMS: {"step_mode": 0},
            },
            (LONG_PRESS, DIM_UP): {
                COMMAND: COMMAND_MOVE_ON_OFF,
                CLUSTER_ID: 8,
                ENDPOINT_ID: 1,
                PARAMS: {"move_mode": 0},
            },
            (SHORT_PRESS, DIM_DOWN): {
                COMMAND: COMMAND_STEP,
                CLUSTER_ID: 8,
                ENDPOINT_ID: 1,
                PARAMS: {"step_mode": 1},
            },
            (LONG_PRESS, DIM_DOWN): {
                COMMAND: COMMAND_MOVE,
                CLUSTER_ID: 8,
                ENDPOINT_ID: 1,
                PARAMS: {"move_mode": 1},
            },
        }
    )
    .add_to_registry()
)
