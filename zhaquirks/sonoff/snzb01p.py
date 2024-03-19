"""Sonoff Smart Button SNZB-01P."""

from zigpy.quirks.v2 import add_to_registry_v2

from zhaquirks.const import (
    BUTTON,
    CLUSTER_ID,
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
    add_to_registry_v2("eWeLink", "SNZB-01P").device_automation_triggers(
        {
            (SHORT_PRESS, BUTTON): {
                COMMAND: COMMAND_TOGGLE,
                CLUSTER_ID: 6,
                ENDPOINT_ID: 1,
            },
            (DOUBLE_PRESS, BUTTON): {
                COMMAND: COMMAND_ON,
                CLUSTER_ID: 6,
                ENDPOINT_ID: 1,
            },
            (LONG_PRESS, BUTTON): {
                COMMAND: COMMAND_OFF,
                CLUSTER_ID: 6,
                ENDPOINT_ID: 1,
            },
        }
    )
)
