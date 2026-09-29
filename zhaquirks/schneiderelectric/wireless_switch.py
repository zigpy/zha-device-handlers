"""Quirk for the Schneider Electric FLS/AIRLINK/4 wireless wall switch."""

from zigpy.zcl.clusters.general import LevelControl, OnOff, PowerConfiguration

from zhaquirks.builder import QuirkBuilder
from zhaquirks.const import (
    CLUSTER_ID,
    COMMAND,
    COMMAND_MOVE,
    COMMAND_MOVE_ON_OFF,
    COMMAND_OFF,
    COMMAND_ON,
    COMMAND_STOP,
    DIM_DOWN,
    DIM_UP,
    ENDPOINT_ID,
    LEFT,
    LONG_RELEASE,
    RIGHT,
    TURN_OFF,
    TURN_ON,
)
from zhaquirks.schneiderelectric import SE_MANUF_NAME

# Battery-powered remote with two rockers. Each rocker sends on/off on a short
# press (OnOff) and level move/stop on a long press/release (LevelControl).
LEFT_EP = 22
RIGHT_EP = 21

(
    QuirkBuilder(SE_MANUF_NAME, "FLS/AIRLINK/4")
    .device_automation_triggers(
        {
            # Left rocker (endpoint 22)
            (TURN_ON, LEFT): {
                COMMAND: COMMAND_ON,
                CLUSTER_ID: OnOff.cluster_id,
                ENDPOINT_ID: LEFT_EP,
            },
            (TURN_OFF, LEFT): {
                COMMAND: COMMAND_OFF,
                CLUSTER_ID: OnOff.cluster_id,
                ENDPOINT_ID: LEFT_EP,
            },
            (DIM_UP, LEFT): {
                COMMAND: COMMAND_MOVE_ON_OFF,
                CLUSTER_ID: LevelControl.cluster_id,
                ENDPOINT_ID: LEFT_EP,
            },
            (DIM_DOWN, LEFT): {
                COMMAND: COMMAND_MOVE,
                CLUSTER_ID: LevelControl.cluster_id,
                ENDPOINT_ID: LEFT_EP,
            },
            (LONG_RELEASE, LEFT): {
                COMMAND: COMMAND_STOP,
                CLUSTER_ID: LevelControl.cluster_id,
                ENDPOINT_ID: LEFT_EP,
            },
            # Right rocker (endpoint 21)
            (TURN_ON, RIGHT): {
                COMMAND: COMMAND_ON,
                CLUSTER_ID: OnOff.cluster_id,
                ENDPOINT_ID: RIGHT_EP,
            },
            (TURN_OFF, RIGHT): {
                COMMAND: COMMAND_OFF,
                CLUSTER_ID: OnOff.cluster_id,
                ENDPOINT_ID: RIGHT_EP,
            },
            (DIM_UP, RIGHT): {
                COMMAND: COMMAND_MOVE_ON_OFF,
                CLUSTER_ID: LevelControl.cluster_id,
                ENDPOINT_ID: RIGHT_EP,
            },
            (DIM_DOWN, RIGHT): {
                COMMAND: COMMAND_MOVE,
                CLUSTER_ID: LevelControl.cluster_id,
                ENDPOINT_ID: RIGHT_EP,
            },
            (LONG_RELEASE, RIGHT): {
                COMMAND: COMMAND_STOP,
                CLUSTER_ID: LevelControl.cluster_id,
                ENDPOINT_ID: RIGHT_EP,
            },
        }
    )
    # Expose a single battery entity: keep endpoint 21 (the main endpoint, which
    # also carries poll control and OTA) and hide the redundant ones.
    .prevent_default_entity_creation(
        endpoint_id=LEFT_EP, cluster_id=PowerConfiguration.cluster_id
    )
    .prevent_default_entity_creation(
        endpoint_id=23, cluster_id=PowerConfiguration.cluster_id
    )
    .prevent_default_entity_creation(
        endpoint_id=24, cluster_id=PowerConfiguration.cluster_id
    )
    .add_to_registry()
)
