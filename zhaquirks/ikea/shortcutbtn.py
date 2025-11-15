"""Device handler for IKEA of Sweden TRADFRI shortcut button."""

from zigpy.quirks.v2 import QuirkBuilder

from zhaquirks.const import (
    CLUSTER_ID,
    COMMAND,
    COMMAND_MOVE_ON_OFF,
    COMMAND_OFF,
    COMMAND_ON,
    COMMAND_STOP_ON_OFF,
    DIM_UP,
    DOUBLE_PRESS,
    ENDPOINT_ID,
    LONG_PRESS,
    LONG_RELEASE,
    PARAMS,
    SHORT_PRESS,
    TURN_ON,
)
from zhaquirks.ikea import IKEA, IKEA_CLUSTER_ID, DoublingPowerConfig1CRCluster

(
    QuirkBuilder(IKEA, "TRADFRI SHORTCUT Button")
    .replaces(DoublingPowerConfig1CRCluster, endpoint_id=1)
    .device_automation_triggers(
        {
            (SHORT_PRESS, TURN_ON): {
                COMMAND: COMMAND_ON,
                CLUSTER_ID: 6,
                ENDPOINT_ID: 1,
            },
            (DOUBLE_PRESS, TURN_ON): {
                COMMAND: COMMAND_OFF,
                CLUSTER_ID: 6,
                ENDPOINT_ID: 1,
            },
            (LONG_PRESS, DIM_UP): {
                COMMAND: COMMAND_MOVE_ON_OFF,
                CLUSTER_ID: 8,
                ENDPOINT_ID: 1,
                PARAMS: {"move_mode": 0},
            },
            (LONG_RELEASE, DIM_UP): {
                COMMAND: COMMAND_STOP_ON_OFF,
                CLUSTER_ID: 8,
                ENDPOINT_ID: 1,
            },
        }
    )
    .add_to_registry()
)


(
    QuirkBuilder(IKEA, "TRADFRI SHORTCUT Button")
    .replaces(DoublingPowerConfig1CRCluster, endpoint_id=1)
    .removes(IKEA_CLUSTER_ID, endpoint_id=1)
    .device_automation_triggers(
        {
            (SHORT_PRESS, TURN_ON): {
                COMMAND: COMMAND_ON,
                CLUSTER_ID: 6,
                ENDPOINT_ID: 1,
            },
            (DOUBLE_PRESS, TURN_ON): {
                COMMAND: COMMAND_OFF,
                CLUSTER_ID: 6,
                ENDPOINT_ID: 1,
            },
            (LONG_PRESS, DIM_UP): {
                COMMAND: COMMAND_MOVE_ON_OFF,
                CLUSTER_ID: 8,
                ENDPOINT_ID: 1,
                PARAMS: {"move_mode": 0},
            },
            (LONG_RELEASE, DIM_UP): {
                COMMAND: COMMAND_STOP_ON_OFF,
                CLUSTER_ID: 8,
                ENDPOINT_ID: 1,
            },
        }
    )
    .add_to_registry()
)
