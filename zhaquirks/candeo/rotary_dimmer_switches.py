"""Candeo rotary dimmer switches."""

from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl import ClusterType
from zigpy.zcl.clusters.general import Identify, Ota

from zhaquirks.candeo import (
    CANDEO,
    COMMAND_CONTINUED_ROTATING,
    COMMAND_DOUBLE_PRESS,
    COMMAND_HOLD,
    COMMAND_PRESS,
    COMMAND_RELEASE,
    COMMAND_STARTED_ROTATING,
    COMMAND_STOPPED_ROTATING,
    CandeoLevelControlRemoteCluster,
    CandeoOnOffRemoteCluster,
)
from zhaquirks.const import CLUSTER_ID, COMMAND, ENDPOINT_ID, PARAMS

remote_quirk = (
    QuirkBuilder()
    .replaces(CandeoOnOffRemoteCluster, endpoint_id=2, cluster_type=ClusterType.Client)
    .replaces(
        CandeoLevelControlRemoteCluster, endpoint_id=2, cluster_type=ClusterType.Client
    )
    .device_automation_triggers(
        {
            ("Pressed", "Rotary knob"): {
                COMMAND: COMMAND_PRESS,
                CLUSTER_ID: 6,
                ENDPOINT_ID: 2,
            },
            ("Double pressed", "Rotary knob"): {
                COMMAND: COMMAND_DOUBLE_PRESS,
                CLUSTER_ID: 6,
                ENDPOINT_ID: 2,
            },
            ("Held", "Rotary knob"): {
                COMMAND: COMMAND_HOLD,
                CLUSTER_ID: 6,
                ENDPOINT_ID: 2,
            },
            ("Released", "Rotary knob"): {
                COMMAND: COMMAND_RELEASE,
                CLUSTER_ID: 6,
                ENDPOINT_ID: 2,
            },
            ("Started rotating left", "Rotary knob"): {
                COMMAND: COMMAND_STARTED_ROTATING,
                CLUSTER_ID: 8,
                ENDPOINT_ID: 2,
                PARAMS: {"direction": 1},
            },
            ("Rotating left", "Rotary knob"): {
                COMMAND: COMMAND_CONTINUED_ROTATING,
                CLUSTER_ID: 8,
                ENDPOINT_ID: 2,
                PARAMS: {"direction": 1},
            },
            ("Started rotating right", "Rotary knob"): {
                COMMAND: COMMAND_STARTED_ROTATING,
                CLUSTER_ID: 8,
                ENDPOINT_ID: 2,
                PARAMS: {"direction": 0},
            },
            ("Rotating right", "Rotary knob"): {
                COMMAND: COMMAND_CONTINUED_ROTATING,
                CLUSTER_ID: 8,
                ENDPOINT_ID: 2,
                PARAMS: {"direction": 0},
            },
            ("Stopped rotating", "Rotary knob"): {
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
