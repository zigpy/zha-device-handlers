"""Device handler for IKEA of Sweden TRADFRI SYMFONISK remote control."""

from zigpy.quirks.v2 import QuirkBuilder

from zhaquirks.const import (
    CLUSTER_ID,
    COMMAND,
    COMMAND_MOVE,
    COMMAND_STEP,
    COMMAND_STOP,
    COMMAND_TOGGLE,
    DOUBLE_PRESS,
    ENDPOINT_ID,
    LEFT,
    PARAMS,
    RIGHT,
    ROTATED,
    SHORT_PRESS,
    STOP,
    TRIPLE_PRESS,
    TURN_ON,
)
from zhaquirks.ikea import (
    IKEA,
    WWAH_CLUSTER_ID,
    DoublingPowerConfig1CRCluster,
    PowerConfig1CRCluster,
)

DEVICE_AUTOMATION_TRIGGERS = {
    (SHORT_PRESS, TURN_ON): {
        COMMAND: COMMAND_TOGGLE,
        CLUSTER_ID: 6,
        ENDPOINT_ID: 1,
    },
    (ROTATED, RIGHT): {
        COMMAND: COMMAND_MOVE,
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
    (ROTATED, STOP): {
        COMMAND: COMMAND_STOP,
        CLUSTER_ID: 8,
        ENDPOINT_ID: 1,
    },
    (DOUBLE_PRESS, TURN_ON): {
        COMMAND: COMMAND_STEP,
        CLUSTER_ID: 8,
        ENDPOINT_ID: 1,
        PARAMS: {"step_mode": 0},
    },
    (TRIPLE_PRESS, TURN_ON): {
        COMMAND: COMMAND_STEP,
        CLUSTER_ID: 8,
        ENDPOINT_ID: 1,
        PARAMS: {"step_mode": 1},
    },
}

(
    QuirkBuilder(IKEA, "SYMFONISK Sound Controller")
    # TODO: identify the exact firmware versions when this fix stopped being required
    .filter(lambda dev: WWAH_CLUSTER_ID not in dev.endpoints[1].in_clusters)
    .replaces(DoublingPowerConfig1CRCluster, endpoint_id=1)
    .device_automation_triggers(DEVICE_AUTOMATION_TRIGGERS)
    .add_to_registry()
)


(
    QuirkBuilder(IKEA, "SYMFONISK Sound Controller")
    # TODO: identify the exact firmware versions when this fix stopped being required
    .filter(lambda dev: WWAH_CLUSTER_ID in dev.endpoints[1].in_clusters)
    .replaces(PowerConfig1CRCluster, endpoint_id=1)
    .device_automation_triggers(DEVICE_AUTOMATION_TRIGGERS)
    .add_to_registry()
)
