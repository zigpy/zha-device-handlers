"""Device handler for Sonoff BASICZBR3."""

from zigpy.quirks.v2 import QuirkBuilder

from zhaquirks.const import (
    CLUSTER_ID,
    COMMAND,
    ENDPOINT_ID,
    LONG_PRESS,
    PARAMS,
    SHORT_PRESS,
)

# Define action types for the BASICZBR3
POWER_ON = "power_on"
FLASH = "flash"

(
    QuirkBuilder("SONOFF", "BASICZBR3")
    .device_automation_triggers(
        {
            # Power On action - uses identify command without parameters
            (POWER_ON,): {
                COMMAND: "identify",
                CLUSTER_ID: 3,  # Identify cluster
                ENDPOINT_ID: 1,
                PARAMS: {"identify_time": 5},
            },
            # Flash Short action - uses trigger_effect command with short flash
            (FLASH, SHORT_PRESS): {
                COMMAND: "trigger_effect",
                CLUSTER_ID: 3,  # Identify cluster
                ENDPOINT_ID: 1,
                PARAMS: {"effect_id": 0x00, "effect_variant": 0x00},  # Short flash
            },
            # Flash Long action - uses trigger_effect command with long flash
            (FLASH, LONG_PRESS): {
                COMMAND: "trigger_effect",
                CLUSTER_ID: 3,  # Identify cluster
                ENDPOINT_ID: 1,
                PARAMS: {"effect_id": 0x00, "effect_variant": 0x01},  # Long flash
            },
        }
    )
    .add_to_registry()
)
