"""Device handler for eWeLink WB01."""
from zigpy.quirks.v2 import add_to_registry_v2

from zhaquirks.const import (
    BUTTON,
    COMMAND,
    COMMAND_OFF,
    COMMAND_ON,
    COMMAND_TOGGLE,
    DOUBLE_PRESS,
    LONG_PRESS,
    SHORT_PRESS,
)

(
    add_to_registry_v2("eWeLink", "WB01").device_automation_triggers(
        {
            (SHORT_PRESS, BUTTON): {COMMAND: COMMAND_TOGGLE},
            (DOUBLE_PRESS, BUTTON): {COMMAND: COMMAND_ON},
            (LONG_PRESS, BUTTON): {COMMAND: COMMAND_OFF},
        }
    )
)
