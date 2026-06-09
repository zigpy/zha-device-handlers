"""Device handler for Insta NEXENTRO Pushbutton Interface."""

from zigpy.quirks.v2 import QuirkBuilder

from zhaquirks.const import (
    ALT_SHORT_PRESS,
    BUTTON,
    CLOSE,
    COMMAND,
    COMMAND_MOVE,
    COMMAND_MOVE_ON_OFF,
    COMMAND_OFF,
    COMMAND_ON,
    COMMAND_STOP,
    COMMAND_TOGGLE,
    DIM_DOWN,
    DIM_UP,
    ENDPOINT_ID,
    OPEN,
    SHORT_PRESS,
    STOP,
    TURN_OFF,
    TURN_ON,
)
from zhaquirks.insta import INSTA

COMMAND_OPEN = "up_open"
COMMAND_CLOSE = "down_close"
COMMAND_STORE = "store"
COMMAND_RECALL = "recall"


(
    QuirkBuilder(INSTA, "NEXENTRO Pushbutton Interface")
    .device_automation_triggers(
        {
            (SHORT_PRESS, TURN_ON): {COMMAND: COMMAND_ON, ENDPOINT_ID: 4},
            (ALT_SHORT_PRESS, TURN_ON): {COMMAND: COMMAND_ON, ENDPOINT_ID: 5},
            (SHORT_PRESS, TURN_OFF): {COMMAND: COMMAND_OFF, ENDPOINT_ID: 4},
            (ALT_SHORT_PRESS, TURN_OFF): {COMMAND: COMMAND_OFF, ENDPOINT_ID: 5},
            (SHORT_PRESS, BUTTON): {COMMAND: COMMAND_TOGGLE, ENDPOINT_ID: 4},
            (ALT_SHORT_PRESS, BUTTON): {COMMAND: COMMAND_TOGGLE, ENDPOINT_ID: 5},
            (SHORT_PRESS, OPEN): {COMMAND: COMMAND_OPEN},
            (SHORT_PRESS, CLOSE): {COMMAND: COMMAND_CLOSE},
            (SHORT_PRESS, DIM_UP): {COMMAND: COMMAND_MOVE_ON_OFF, ENDPOINT_ID: 4},
            (ALT_SHORT_PRESS, DIM_UP): {COMMAND: COMMAND_MOVE_ON_OFF, ENDPOINT_ID: 5},
            (SHORT_PRESS, DIM_DOWN): {COMMAND: COMMAND_MOVE, ENDPOINT_ID: 4},
            (ALT_SHORT_PRESS, DIM_DOWN): {COMMAND: COMMAND_MOVE, ENDPOINT_ID: 5},
            (SHORT_PRESS, STOP): {COMMAND: COMMAND_STOP, ENDPOINT_ID: 4},
            (ALT_SHORT_PRESS, STOP): {COMMAND: COMMAND_STOP, ENDPOINT_ID: 5},
        }
    )
    .add_to_registry()
)
