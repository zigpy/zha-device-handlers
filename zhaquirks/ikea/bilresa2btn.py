"""IKEA Bilresa 2 button remote control."""

from zigpy.zcl import ClusterType
from zigpy.zcl.clusters.general import LevelControl, OnOff, Scenes

from zhaquirks.builder import QuirkBuilder
from zhaquirks.const import (
    CLUSTER_ID,
    COMMAND,
    COMMAND_OFF,
    COMMAND_ON,
    DIM_DOWN,
    DIM_UP,
    DOUBLE_PRESS,
    ENDPOINT_ID,
    LONG_PRESS,
    LONG_RELEASE,
    SHORT_PRESS,
    TURN_OFF,
    TURN_ON,
)
from zhaquirks.ikea import IKEA, IkeaBilresaLevelControl, IkeaBilresaScenesCluster

(
    QuirkBuilder(IKEA, "09B9")
    .replaces(IkeaBilresaScenesCluster, cluster_type=ClusterType.Client)
    .replace_cluster_occurrences(IkeaBilresaLevelControl)
    .device_automation_triggers(
        {
            (SHORT_PRESS, TURN_ON): {
                COMMAND: COMMAND_ON,
                CLUSTER_ID: OnOff.cluster_id,
                ENDPOINT_ID: 1,
            },
            (LONG_PRESS, DIM_UP): {
                COMMAND: "move_up_press",
                CLUSTER_ID: LevelControl.cluster_id,
                ENDPOINT_ID: 1,
            },
            (LONG_RELEASE, DIM_UP): {
                COMMAND: "move_up_release",
                CLUSTER_ID: LevelControl.cluster_id,
                ENDPOINT_ID: 1,
            },
            (SHORT_PRESS, TURN_OFF): {
                COMMAND: COMMAND_OFF,
                CLUSTER_ID: OnOff.cluster_id,
                ENDPOINT_ID: 1,
            },
            (LONG_PRESS, DIM_DOWN): {
                COMMAND: "move_down_press",
                CLUSTER_ID: LevelControl.cluster_id,
                ENDPOINT_ID: 1,
            },
            (LONG_RELEASE, DIM_DOWN): {
                COMMAND: "move_down_release",
                CLUSTER_ID: LevelControl.cluster_id,
                ENDPOINT_ID: 1,
            },
            (DOUBLE_PRESS, DIM_UP): {
                COMMAND: "double_press_dim_up",
                CLUSTER_ID: Scenes.cluster_id,
                ENDPOINT_ID: 1,
            },
            (DOUBLE_PRESS, DIM_DOWN): {
                COMMAND: "double_press_dim_down",
                CLUSTER_ID: Scenes.cluster_id,
                ENDPOINT_ID: 1,
            },
        }
    )
    .add_to_registry()
)
