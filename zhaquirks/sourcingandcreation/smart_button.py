"""Device handler for Sourcing & Creation EB-SB-1B (Boulanger Essentielb 8009289) smart button."""

from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl.clusters.general import LevelControl, OnOff
from zigpy.zcl.clusters.lighting import Color

from zhaquirks.const import (
    CLUSTER_ID,
    COMMAND,
    COMMAND_STEP,
    COMMAND_STEP_COLOR_TEMP,
    COMMAND_STOP,
    DOUBLE_PRESS,
    ENDPOINT_ID,
    LONG_PRESS,
    LONG_RELEASE,
    SHORT_PRESS,
    TURN_ON,
)

(
    QuirkBuilder("Sourcing & Creation", "EB-SB-1B")
    .device_automation_triggers(
        {
            (SHORT_PRESS, TURN_ON): {
                CLUSTER_ID: OnOff.cluster_id,
                ENDPOINT_ID: 1,
            },
            (LONG_PRESS, TURN_ON): {
                COMMAND: COMMAND_STEP,
                CLUSTER_ID: LevelControl.cluster_id,
                ENDPOINT_ID: 1,
            },
            (LONG_RELEASE, TURN_ON): {
                COMMAND: COMMAND_STOP,
                CLUSTER_ID: LevelControl.cluster_id,
                ENDPOINT_ID: 1,
            },
            (DOUBLE_PRESS, TURN_ON): {
                COMMAND: COMMAND_STEP_COLOR_TEMP,
                CLUSTER_ID: Color.cluster_id,
                ENDPOINT_ID: 1,
            },
        }
    )
    .add_to_registry()
)
