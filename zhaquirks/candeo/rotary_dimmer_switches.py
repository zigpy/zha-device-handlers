"""Candeo rotary dimmer switches."""

from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl import ClusterType
from zigpy.zcl.clusters.general import Identify, Ota

from zhaquirks.candeo import (
    CANDEO,
    CandeoLevelControlRemoteCluster,
    CandeoOnOffRemoteCluster,
)
from zhaquirks.const import (
    CLUSTER_ID,
    COMMAND,
    COMMAND_CONTINUED_ROTATING,
    COMMAND_DOUBLE,
    COMMAND_HOLD,
    COMMAND_PRESS,
    COMMAND_RELEASE,
    COMMAND_STARTED_ROTATING,
    COMMAND_STOPPED_ROTATING,
    CONTINUED_ROTATING,
    DOUBLE_PRESS,
    ENDPOINT_ID,
    LEFT,
    LONG_PRESS,
    LONG_RELEASE,
    PARAMS,
    RIGHT,
    ROTARY_KNOB,
    SHORT_PRESS,
    STARTED_ROTATING,
    STOPPED_ROTATING,
)

remote_quirk = (
    QuirkBuilder()
    .replaces(
        CandeoOnOffRemoteCluster,
        endpoint_id=2,
        cluster_type=ClusterType.Client,
    )
    .replaces(
        CandeoLevelControlRemoteCluster,
        endpoint_id=2,
        cluster_type=ClusterType.Client,
    )
    .device_automation_triggers(
        {
            (SHORT_PRESS, ROTARY_KNOB): {
                COMMAND: COMMAND_PRESS,
                CLUSTER_ID: 6,
                ENDPOINT_ID: 2,
            },
            (DOUBLE_PRESS, ROTARY_KNOB): {
                COMMAND: COMMAND_DOUBLE,
                CLUSTER_ID: 6,
                ENDPOINT_ID: 2,
            },
            (LONG_PRESS, ROTARY_KNOB): {
                COMMAND: COMMAND_HOLD,
                CLUSTER_ID: 6,
                ENDPOINT_ID: 2,
            },
            (LONG_RELEASE, ROTARY_KNOB): {
                COMMAND: COMMAND_RELEASE,
                CLUSTER_ID: 6,
                ENDPOINT_ID: 2,
            },
            (STARTED_ROTATING, LEFT): {
                COMMAND: COMMAND_STARTED_ROTATING,
                CLUSTER_ID: 8,
                ENDPOINT_ID: 2,
                PARAMS: {"direction": 1},
            },
            (CONTINUED_ROTATING, LEFT): {
                COMMAND: COMMAND_CONTINUED_ROTATING,
                CLUSTER_ID: 8,
                ENDPOINT_ID: 2,
                PARAMS: {"direction": 1},
            },
            (STARTED_ROTATING, RIGHT): {
                COMMAND: COMMAND_STARTED_ROTATING,
                CLUSTER_ID: 8,
                ENDPOINT_ID: 2,
                PARAMS: {"direction": 0},
            },
            (CONTINUED_ROTATING, RIGHT): {
                COMMAND: COMMAND_CONTINUED_ROTATING,
                CLUSTER_ID: 8,
                ENDPOINT_ID: 2,
                PARAMS: {"direction": 0},
            },
            (STOPPED_ROTATING, ROTARY_KNOB): {
                COMMAND: COMMAND_STOPPED_ROTATING,
                CLUSTER_ID: 8,
                ENDPOINT_ID: 2,
            },
        }
    )
)

(
    QuirkBuilder(CANDEO, "C-ZB-RD1")
    .applies_to(CANDEO, "C-ZB-RD1P-DIM")
    .removes(Ota.cluster_id)
    .add_to_registry()
)

(
    remote_quirk.clone()
    .applies_to(CANDEO, "C-ZB-RD1P-REM")
    .removes(Identify.cluster_id, endpoint_id=1)
    .removes(Identify.cluster_id, endpoint_id=2)
    .removes(Ota.cluster_id)
    .add_to_registry()
)

(
    remote_quirk.clone()
    .applies_to(CANDEO, "C-ZB-RD1P-DPM")
    .removes(Ota.cluster_id)
    .add_to_registry()
)
