"""icasa KPD12 device."""

from zigpy.quirks.v2 import QuirkBuilder

from zhaquirks.const import (
    BUTTON,
    CLUSTER_ID,
    COMMAND,
    COMMAND_MOVE_ON_OFF,
    COMMAND_OFF,
    COMMAND_ON,
    COMMAND_STOP,
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
    QuirkBuilder("icasa", "ICZB-KPD12")
    .device_automation_triggers(
        {
            (SHORT_PRESS, TURN_ON): {
                COMMAND: COMMAND_ON,
                ENDPOINT_ID: 1,
                CLUSTER_ID: 6,
            },
            (LONG_PRESS, DIM_UP): {
                COMMAND: COMMAND_MOVE_ON_OFF,
                ENDPOINT_ID: 1,
                CLUSTER_ID: 8,
                PARAMS: {"move_mode": 0, "rate": 50},
            },
            (LONG_RELEASE, BUTTON): {
                COMMAND: COMMAND_STOP,
                ENDPOINT_ID: 1,
                CLUSTER_ID: 8,
            },
            (SHORT_PRESS, TURN_OFF): {
                COMMAND: COMMAND_OFF,
                ENDPOINT_ID: 1,
                CLUSTER_ID: 6,
            },
            (LONG_PRESS, DIM_DOWN): {
                COMMAND: COMMAND_MOVE_ON_OFF,
                ENDPOINT_ID: 1,
                CLUSTER_ID: 8,
                PARAMS: {"move_mode": 1, "rate": 50},
            },
        }
    )
    .add_to_registry()
)
