"""Device handler for Lutron LZL4BWHL01 Remote."""

from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl import ClusterType
from zigpy.zcl.clusters.general import LevelControl, OnOff

from zhaquirks import GroupBoundCluster
from zhaquirks.const import (
    CLUSTER_ID,
    COMMAND,
    COMMAND_MOVE_TO_LEVEL_ON_OFF,
    COMMAND_STEP,
    COMMAND_STEP_ON_OFF,
    DIM_DOWN,
    DIM_UP,
    ENDPOINT_ID,
    PARAMS,
    SHORT_PRESS,
    TURN_OFF,
    TURN_ON,
)

MANUFACTURER_SPECIFIC_CLUSTER_ID_1 = 0xFF00  # decimal = 65280
MANUFACTURER_SPECIFIC_CLUSTER_ID_2 = 0xFC44  # decimal = 64580


class OnOffGroupCluster(GroupBoundCluster, OnOff):
    """On/Off Cluster which only binds to a group."""


class LevelControlGroupCluster(GroupBoundCluster, LevelControl):
    """Level Control Cluster which only binds to a group."""


(
    QuirkBuilder("Lutron", "LZL4BWHL01 Remote")
    .applies_to(" Lutron", "LZL4BWHL01 Remote")
    .replaces(OnOffGroupCluster, cluster_type=ClusterType.Client, endpoint_id=1)
    .replaces(LevelControlGroupCluster, cluster_type=ClusterType.Client, endpoint_id=1)
    .device_automation_triggers(
        {
            (SHORT_PRESS, TURN_ON): {
                COMMAND: COMMAND_MOVE_TO_LEVEL_ON_OFF,
                CLUSTER_ID: 8,
                ENDPOINT_ID: 1,
                PARAMS: {"level": 254, "transition_time": 4},
            },
            (SHORT_PRESS, TURN_OFF): {
                COMMAND: COMMAND_MOVE_TO_LEVEL_ON_OFF,
                CLUSTER_ID: 8,
                ENDPOINT_ID: 1,
                PARAMS: {"level": 0, "transition_time": 4},
            },
            (SHORT_PRESS, DIM_UP): {
                COMMAND: COMMAND_STEP_ON_OFF,
                CLUSTER_ID: 8,
                ENDPOINT_ID: 1,
                PARAMS: {"step_mode": 0},
            },
            (SHORT_PRESS, DIM_DOWN): {
                COMMAND: COMMAND_STEP,
                CLUSTER_ID: 8,
                ENDPOINT_ID: 1,
                PARAMS: {"step_mode": 1},
            },
        }
    )
    .add_to_registry()
)
