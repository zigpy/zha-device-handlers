"""Device handler for Sonoff buttons."""

from zigpy.quirks.v2 import QuirkBuilder

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
    QuirkBuilder("eWeLink", "WB01")
    .also_applies_to("eWeLink", "SNZB-01P")
    .also_applies_to("eWeLink", "CK-TLSR8656-SS5-01(7000)")
    .device_automation_triggers(
        {
            (SHORT_PRESS, BUTTON): {COMMAND: COMMAND_TOGGLE},
            (DOUBLE_PRESS, BUTTON): {COMMAND: COMMAND_ON},
            (LONG_PRESS, BUTTON): {COMMAND: COMMAND_OFF},
        }
    )
    .add_to_registry()
)
