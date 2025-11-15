"""Device handler for Paulmann 4-button remote control."""

from zigpy.quirks.v2 import QuirkBuilder

from zhaquirks.const import (
    BUTTON_1,
    BUTTON_2,
    BUTTON_3,
    BUTTON_4,
    CLUSTER_ID,
    COMMAND,
    COMMAND_MOVE_ON_OFF,
    COMMAND_OFF,
    COMMAND_ON,
    COMMAND_STOP_ON_OFF,
    ENDPOINT_ID,
    LONG_PRESS,
    LONG_RELEASE,
    PARAMS,
    SHORT_PRESS,
)
from zhaquirks.paulmann import PAULMANN, PAULMANN_VARIANT

(
    QuirkBuilder(PAULMANN, "501.34")
    .applies_to(PAULMANN_VARIANT, "501.34")
    .device_automation_triggers(
        {
            (SHORT_PRESS, BUTTON_1): {
                COMMAND: COMMAND_ON,
                CLUSTER_ID: 6,
                ENDPOINT_ID: 1,
            },
            (LONG_PRESS, BUTTON_1): {
                COMMAND: COMMAND_MOVE_ON_OFF,
                CLUSTER_ID: 8,
                ENDPOINT_ID: 1,
                PARAMS: {"move_mode": 0, "rate": 50},
            },
            (LONG_RELEASE, BUTTON_1): {
                COMMAND: COMMAND_STOP_ON_OFF,
                CLUSTER_ID: 8,
                ENDPOINT_ID: 1,
            },
            (SHORT_PRESS, BUTTON_2): {
                COMMAND: COMMAND_OFF,
                CLUSTER_ID: 6,
                ENDPOINT_ID: 1,
            },
            (LONG_PRESS, BUTTON_2): {
                COMMAND: COMMAND_MOVE_ON_OFF,
                CLUSTER_ID: 8,
                ENDPOINT_ID: 1,
                PARAMS: {"move_mode": 1, "rate": 50},
            },
            (LONG_RELEASE, BUTTON_2): {
                COMMAND: COMMAND_STOP_ON_OFF,
                CLUSTER_ID: 8,
                ENDPOINT_ID: 1,
            },
            (SHORT_PRESS, BUTTON_3): {
                COMMAND: COMMAND_ON,
                CLUSTER_ID: 6,
                ENDPOINT_ID: 2,
            },
            (LONG_PRESS, BUTTON_3): {
                COMMAND: COMMAND_MOVE_ON_OFF,
                CLUSTER_ID: 8,
                ENDPOINT_ID: 2,
                PARAMS: {"move_mode": 0, "rate": 50},
            },
            (LONG_RELEASE, BUTTON_3): {
                COMMAND: COMMAND_STOP_ON_OFF,
                CLUSTER_ID: 8,
                ENDPOINT_ID: 2,
            },
            (SHORT_PRESS, BUTTON_4): {
                COMMAND: COMMAND_OFF,
                CLUSTER_ID: 6,
                ENDPOINT_ID: 2,
            },
            (LONG_PRESS, BUTTON_4): {
                COMMAND: COMMAND_MOVE_ON_OFF,
                CLUSTER_ID: 8,
                ENDPOINT_ID: 2,
                PARAMS: {"move_mode": 1, "rate": 50},
            },
            (LONG_RELEASE, BUTTON_4): {
                COMMAND: COMMAND_STOP_ON_OFF,
                CLUSTER_ID: 8,
                ENDPOINT_ID: 2,
            },
        }
    )
    .add_to_registry()
)
