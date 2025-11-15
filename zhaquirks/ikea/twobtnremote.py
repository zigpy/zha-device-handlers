"""Device handler for IKEA of Sweden TRADFRI remote control."""

from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl.clusters.closures import WindowCovering
from zigpy.zcl.clusters.general import Groups

from zhaquirks.const import (
    CLUSTER_ID,
    COMMAND,
    COMMAND_MOVE,
    COMMAND_MOVE_ON_OFF,
    COMMAND_OFF,
    COMMAND_ON,
    COMMAND_STOP,
    COMMAND_STOP_ON_OFF,
    DIM_DOWN,
    DIM_UP,
    ENDPOINT_ID,
    LONG_PRESS,
    LONG_RELEASE,
    PARAMS,
    SHORT_PRESS,
    TURN_OFF,
    TURN_ON,
)
from zhaquirks.ikea import IKEA, DoublingPowerConfig1CRCluster, PowerConfig1AAACluster

_DEVICE_AUTOMATION_TRIGGERS = {
    (SHORT_PRESS, TURN_ON): {COMMAND: COMMAND_ON, CLUSTER_ID: 6, ENDPOINT_ID: 1},
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
    (SHORT_PRESS, TURN_OFF): {COMMAND: COMMAND_OFF, CLUSTER_ID: 6, ENDPOINT_ID: 1},
    (LONG_PRESS, DIM_DOWN): {
        COMMAND: COMMAND_MOVE,
        CLUSTER_ID: 8,
        ENDPOINT_ID: 1,
        PARAMS: {"move_mode": 1},
    },
    (LONG_RELEASE, DIM_DOWN): {
        COMMAND: COMMAND_STOP,
        CLUSTER_ID: 8,
        ENDPOINT_ID: 1,
    },
}

(
    QuirkBuilder(IKEA, "TRADFRI on/off switch")
    .replaces(DoublingPowerConfig1CRCluster, endpoint_id=1)
    .device_automation_triggers(_DEVICE_AUTOMATION_TRIGGERS)
    .add_to_registry()
)


# ZLL profile variant
(
    QuirkBuilder(IKEA, "TRADFRI on/off switch")
    .replaces(DoublingPowerConfig1CRCluster, endpoint_id=1)
    .removes(WindowCovering.cluster_id, endpoint_id=1)
    .device_automation_triggers(_DEVICE_AUTOMATION_TRIGGERS)
    .add_to_registry()
)


(
    QuirkBuilder(IKEA, "RODRET Dimmer")
    .replaces(PowerConfig1AAACluster, endpoint_id=1)
    .device_automation_triggers(_DEVICE_AUTOMATION_TRIGGERS)
    .add_to_registry()
)


(
    QuirkBuilder(IKEA, "RODRET Dimmer")
    .applies_to(IKEA, "RODRET wireless dimmer")
    .replaces(PowerConfig1AAACluster, endpoint_id=1)
    .removes(Groups.cluster_id, endpoint_id=1)
    .device_automation_triggers(_DEVICE_AUTOMATION_TRIGGERS)
    .add_to_registry()
)
