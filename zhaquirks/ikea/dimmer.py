"""Device handler for IKEA of Sweden TRADFRI wireless dimmer ICTC-G-1."""

from zigpy.quirks.v2 import QuirkBuilder

from zhaquirks.const import (
    CLUSTER_ID,
    COMMAND,
    COMMAND_MOVE,
    COMMAND_MOVE_ON_OFF,
    ENDPOINT_ID,
    LEFT,
    PARAMS,
    RIGHT,
    ROTATED,
)
from zhaquirks.ikea import IKEA, DoublingPowerConfig1CRXCluster

(
    QuirkBuilder(IKEA, "TRADFRI wireless dimmer")
    .replaces(DoublingPowerConfig1CRXCluster, endpoint_id=1)
    .device_automation_triggers(
        {
            (ROTATED, RIGHT): {
                COMMAND: COMMAND_MOVE_ON_OFF,
                CLUSTER_ID: 8,
                ENDPOINT_ID: 1,
                PARAMS: {"move_mode": 0},
            },
            (ROTATED, LEFT): {
                COMMAND: COMMAND_MOVE,
                CLUSTER_ID: 8,
                ENDPOINT_ID: 1,
                PARAMS: {"move_mode": 1},
            },
        }
    )
    .add_to_registry()
)
