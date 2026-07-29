"""IKEA Bilresa rotary (scroll wheel) remote control."""

from zigpy.zcl import ClusterType
from zigpy.zcl.clusters.general import LevelControl, OnOff, Scenes

from zhaquirks.builder import QuirkBuilder
from zhaquirks.const import (
    CLUSTER_ID,
    COMMAND,
    COMMAND_MOVE_TO_LEVEL,
    COMMAND_OFF,
    COMMAND_ON,
    COMMAND_PRESS,
    DOUBLE_PRESS,
    ENDPOINT_ID,
    PARAMS,
    ROTARY_KNOB,
    ROTATED,
    SHORT_PRESS,
    TURN_OFF,
    TURN_ON,
)
from zhaquirks.ikea import IKEA, ScenesCluster

(
    QuirkBuilder(IKEA, "09BA")
    .subscribes_to_multicast_group(0x549A)
    .subscribes_to_multicast_group(0x549B)
    .subscribes_to_multicast_group(0x549C)
    .subscribes_to_multicast_group(0xFF09)
    .replaces(ScenesCluster, cluster_type=ClusterType.Client)
    .device_automation_triggers(
        {
            (SHORT_PRESS, TURN_ON): {
                COMMAND: COMMAND_ON,
                CLUSTER_ID: OnOff.cluster_id,
                ENDPOINT_ID: 1,
            },
            (SHORT_PRESS, TURN_OFF): {
                COMMAND: COMMAND_OFF,
                CLUSTER_ID: OnOff.cluster_id,
                ENDPOINT_ID: 1,
            },
            # The scroll wheel reports an absolute level, so neither the direction
            # it turned nor a release can be recovered from the command
            (ROTATED, ROTARY_KNOB): {
                COMMAND: COMMAND_MOVE_TO_LEVEL,
                CLUSTER_ID: LevelControl.cluster_id,
                ENDPOINT_ID: 1,
            },
            (DOUBLE_PRESS, TURN_ON): {
                COMMAND: COMMAND_PRESS,
                CLUSTER_ID: Scenes.cluster_id,
                ENDPOINT_ID: 1,
                PARAMS: {
                    "param1": 256,
                    "param2": 13,
                    "param3": 0,
                },
            },
            (DOUBLE_PRESS, TURN_OFF): {
                COMMAND: COMMAND_PRESS,
                CLUSTER_ID: Scenes.cluster_id,
                ENDPOINT_ID: 1,
                PARAMS: {
                    "param1": 257,
                    "param2": 13,
                    "param3": 0,
                },
            },
        }
    )
    .add_to_registry()
)
