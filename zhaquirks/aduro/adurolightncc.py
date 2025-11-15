"""ADUROLIGHT Adurolight_NCC device."""

from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl.clusters.general import LevelControl

from zhaquirks.const import (
    CLUSTER_ID,
    COMMAND,
    COMMAND_OFF,
    COMMAND_ON,
    COMMAND_STEP,
    DIM_DOWN,
    DIM_UP,
    ENDPOINT_ID,
    PARAMS,
    SHORT_PRESS,
    TURN_OFF,
    TURN_ON,
)

ADUROLIGHT_CLUSTER_ID = 64716


(
    QuirkBuilder("ADUROLIGHT", "Adurolight_NCC")
    .removes(LevelControl, endpoint_id=1)
    .device_automation_triggers(
        {
            (SHORT_PRESS, TURN_ON): {
                COMMAND: COMMAND_ON,
                CLUSTER_ID: 6,
                ENDPOINT_ID: 1,
            },
            (SHORT_PRESS, TURN_OFF): {
                COMMAND: COMMAND_OFF,
                CLUSTER_ID: 6,
                ENDPOINT_ID: 1,
            },
            (SHORT_PRESS, DIM_UP): {
                COMMAND: COMMAND_STEP,
                CLUSTER_ID: 8,
                ENDPOINT_ID: 1,
                PARAMS: {"step_mode": 0},
            },
            (SHORT_PRESS, DIM_DOWN): {
                COMMAND: COMMAND_STEP,
                CLUSTER_ID: 8,
                ENDPOINT_ID: 1,
                PARAMS: {"step_mode": 1},
            },
        }
    )
    .add_to_registry()
)
