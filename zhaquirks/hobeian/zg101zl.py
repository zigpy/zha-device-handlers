"""Quirk for the HOBEIAN ZG-101ZL Zigbee button."""

from zhaquirks.builder import QuirkBuilder
from zhaquirks.const import (
    BUTTON,
    COMMAND,
    COMMAND_OFF,
    COMMAND_ON,
    COMMAND_TOGGLE,
    DOUBLE_PRESS,
    ENDPOINT_ID,
    LONG_PRESS,
    SHORT_PRESS,
)

(
    QuirkBuilder("HOBEIAN", "ZG-101ZL")
    .device_automation_triggers(
        {
            (SHORT_PRESS, BUTTON): {
                COMMAND: COMMAND_TOGGLE,
                ENDPOINT_ID: 1,
            },
            (DOUBLE_PRESS, BUTTON): {
                COMMAND: COMMAND_ON,
                ENDPOINT_ID: 1,
            },
            (LONG_PRESS, BUTTON): {
                COMMAND: COMMAND_OFF,
                ENDPOINT_ID: 1,
            },
        }
    )
    .add_to_registry()
)
