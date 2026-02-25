"""Ubisys Control Unit C4 quirk."""

from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl.clusters.general import OnOff

from zhaquirks.const import (
    BUTTON_1,
    BUTTON_2,
    BUTTON_3,
    BUTTON_4,
    CLUSTER_ID,
    COMMAND,
    COMMAND_CLICK,
    ENDPOINT_ID,
)

(
    QuirkBuilder(manufacturer="ubisys", model="C4 (5504)")
    .device_automation_triggers(
        {
            (COMMAND_CLICK, BUTTON_1): {
                ENDPOINT_ID: 1,
                CLUSTER_ID: OnOff.cluster_id,
                COMMAND: OnOff.ServerCommandDefs.toggle.name,
            },
            (COMMAND_CLICK, BUTTON_2): {
                ENDPOINT_ID: 2,
                CLUSTER_ID: OnOff.cluster_id,
                COMMAND: OnOff.ServerCommandDefs.toggle.name,
            },
            (COMMAND_CLICK, BUTTON_3): {
                ENDPOINT_ID: 3,
                CLUSTER_ID: OnOff.cluster_id,
                COMMAND: OnOff.ServerCommandDefs.toggle.name,
            },
            (COMMAND_CLICK, BUTTON_4): {
                ENDPOINT_ID: 4,
                CLUSTER_ID: OnOff.cluster_id,
                COMMAND: OnOff.ServerCommandDefs.toggle.name,
            },
        }
    )
    .add_to_registry()
)
