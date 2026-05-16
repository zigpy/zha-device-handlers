"""Sunricher Button device."""

from zigpy.quirks.v2 import QuirkBuilder

from zhaquirks.const import (
    COMMAND,
    COMMAND_MOVE_ON_OFF,
    COMMAND_OFF,
    COMMAND_ON,
    COMMAND_STOP_ON_OFF,
    LONG_PRESS,
    LONG_RELEASE,
    RIGHT,
    SHORT_PRESS,
    TURN_OFF,
    TURN_ON,
)

(
    QuirkBuilder("Sunricher", "ZGRC-KEY-004")
    .device_automation_triggers(
        {
            (SHORT_PRESS, TURN_ON): {COMMAND: COMMAND_ON},
            (SHORT_PRESS, TURN_OFF): {COMMAND: COMMAND_OFF},
            (LONG_PRESS, RIGHT): {COMMAND: COMMAND_MOVE_ON_OFF},
            (LONG_RELEASE, RIGHT): {COMMAND: COMMAND_STOP_ON_OFF},
        }
    )
    .add_to_registry()
)
