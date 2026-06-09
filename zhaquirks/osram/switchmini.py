"""Osram Smart+ Switch Mini device."""

from zigpy.quirks.v2 import QuirkBuilder

from zhaquirks.const import (
    BUTTON_1,
    BUTTON_2,
    BUTTON_3,
    COMMAND,
    COMMAND_MOVE,
    COMMAND_MOVE_ON_OFF,
    COMMAND_MOVE_TO_LEVEL_ON_OFF,
    COMMAND_OFF,
    COMMAND_ON,
    COMMAND_STOP,
    COMMAND_STOP_ON_OFF,
    ENDPOINT_ID,
    LONG_PRESS,
    LONG_RELEASE,
    SHORT_PRESS,
)
from zhaquirks.osram import OSRAM

(
    QuirkBuilder(OSRAM, "Lightify Switch Mini")
    .device_automation_triggers(
        {
            (SHORT_PRESS, BUTTON_1): {COMMAND: COMMAND_ON, ENDPOINT_ID: 1},
            (LONG_PRESS, BUTTON_1): {COMMAND: COMMAND_MOVE_ON_OFF, ENDPOINT_ID: 1},
            (LONG_RELEASE, BUTTON_1): {COMMAND: COMMAND_STOP_ON_OFF, ENDPOINT_ID: 1},
            (SHORT_PRESS, BUTTON_2): {
                COMMAND: COMMAND_MOVE_TO_LEVEL_ON_OFF,
                ENDPOINT_ID: 3,
            },
            (LONG_PRESS, BUTTON_2): {COMMAND: "move_to_saturation", ENDPOINT_ID: 3},
            (LONG_RELEASE, BUTTON_2): {COMMAND: "move_hue", ENDPOINT_ID: 3},
            (SHORT_PRESS, BUTTON_3): {COMMAND: COMMAND_OFF, ENDPOINT_ID: 2},
            (LONG_PRESS, BUTTON_3): {COMMAND: COMMAND_MOVE, ENDPOINT_ID: 2},
            (LONG_RELEASE, BUTTON_3): {COMMAND: COMMAND_STOP, ENDPOINT_ID: 2},
        }
    )
    .add_to_registry()
)
