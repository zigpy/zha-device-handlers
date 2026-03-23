"""Module for Legrand wireless switches (Radiant, NLD, NLT, NLW)."""

from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl.clusters.general import BinaryInput

from zhaquirks.const import (
    BUTTON,
    BUTTON_1,
    BUTTON_2,
    BUTTON_3,
    COMMAND,
    COMMAND_MOVE,
    COMMAND_OFF,
    COMMAND_ON,
    COMMAND_STOP,
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
from zhaquirks.legrand import LEGRAND, LegrandPowerConfigurationCluster

(
    QuirkBuilder(f" {LEGRAND}", " Remote switch")
    .replaces(LegrandPowerConfigurationCluster)
    .prevent_default_entity_creation(endpoint_id=1, cluster_id=BinaryInput.cluster_id)
    .device_automation_triggers(
        {
            (SHORT_PRESS, TURN_ON): {COMMAND: COMMAND_ON},
            (LONG_PRESS, TURN_ON): {
                COMMAND: COMMAND_MOVE,
                PARAMS: {"move_mode": 0, "rate": 255},
            },
            (SHORT_PRESS, TURN_OFF): {COMMAND: COMMAND_OFF},
            (LONG_PRESS, TURN_OFF): {
                COMMAND: COMMAND_MOVE,
                PARAMS: {"move_mode": 1, "rate": 255},
            },
            (LONG_RELEASE, BUTTON): {COMMAND: COMMAND_STOP},
        }
    )
    .add_to_registry()
)

(
    QuirkBuilder(f" {LEGRAND}", " NLWO - Triple remote switch")
    .replaces(LegrandPowerConfigurationCluster)
    .prevent_default_entity_creation(endpoint_id=1, cluster_id=BinaryInput.cluster_id)
    .device_automation_triggers(
        {
            (TURN_ON, BUTTON_1): {COMMAND: COMMAND_ON, ENDPOINT_ID: 1},
            (DIM_UP, BUTTON_1): {
                COMMAND: COMMAND_MOVE,
                ENDPOINT_ID: 1,
                PARAMS: {"move_mode": 0, "rate": 255},
            },
            (TURN_OFF, BUTTON_1): {COMMAND: COMMAND_OFF},
            (DIM_DOWN, BUTTON_1): {
                COMMAND: COMMAND_MOVE,
                ENDPOINT_ID: 1,
                PARAMS: {"move_mode": 1, "rate": 255},
            },
            (LONG_RELEASE, BUTTON_1): {COMMAND: COMMAND_STOP, ENDPOINT_ID: 1},
            (TURN_ON, BUTTON_2): {COMMAND: COMMAND_ON, ENDPOINT_ID: 2},
            (DIM_UP, BUTTON_2): {
                COMMAND: COMMAND_MOVE,
                ENDPOINT_ID: 2,
                PARAMS: {"move_mode": 0, "rate": 255},
            },
            (TURN_OFF, BUTTON_2): {COMMAND: COMMAND_OFF},
            (DIM_DOWN, BUTTON_2): {
                COMMAND: COMMAND_MOVE,
                ENDPOINT_ID: 2,
                PARAMS: {"move_mode": 1, "rate": 255},
            },
            (LONG_RELEASE, BUTTON_2): {COMMAND: COMMAND_STOP, ENDPOINT_ID: 2},
            (TURN_ON, BUTTON_3): {COMMAND: COMMAND_ON, ENDPOINT_ID: 3},
            (DIM_UP, BUTTON_3): {
                COMMAND: COMMAND_MOVE,
                ENDPOINT_ID: 3,
                PARAMS: {"move_mode": 0, "rate": 255},
            },
            (TURN_OFF, BUTTON_3): {COMMAND: COMMAND_OFF},
            (DIM_DOWN, BUTTON_3): {
                COMMAND: COMMAND_MOVE,
                ENDPOINT_ID: 3,
                PARAMS: {"move_mode": 1, "rate": 255},
            },
            (LONG_RELEASE, BUTTON_3): {COMMAND: COMMAND_STOP, ENDPOINT_ID: 3},
        }
    )
    .add_to_registry()
)

(
    QuirkBuilder(f" {LEGRAND}", " Double gangs remote switch")
    .replaces(LegrandPowerConfigurationCluster)
    .prevent_default_entity_creation(endpoint_id=1, cluster_id=BinaryInput.cluster_id)
    .device_automation_triggers(
        {
            (TURN_ON, BUTTON_1): {COMMAND: COMMAND_ON, ENDPOINT_ID: 1},
            (DIM_UP, BUTTON_1): {
                COMMAND: COMMAND_MOVE,
                ENDPOINT_ID: 1,
                PARAMS: {"move_mode": 0, "rate": 255},
            },
            (TURN_OFF, BUTTON_1): {COMMAND: COMMAND_OFF},
            (DIM_DOWN, BUTTON_1): {
                COMMAND: COMMAND_MOVE,
                ENDPOINT_ID: 1,
                PARAMS: {"move_mode": 1, "rate": 255},
            },
            (LONG_RELEASE, BUTTON_1): {COMMAND: COMMAND_STOP, ENDPOINT_ID: 1},
            (TURN_ON, BUTTON_2): {COMMAND: COMMAND_ON, ENDPOINT_ID: 2},
            (DIM_UP, BUTTON_2): {
                COMMAND: COMMAND_MOVE,
                ENDPOINT_ID: 2,
                PARAMS: {"move_mode": 0, "rate": 255},
            },
            (TURN_OFF, BUTTON_2): {COMMAND: COMMAND_OFF},
            (DIM_DOWN, BUTTON_2): {
                COMMAND: COMMAND_MOVE,
                ENDPOINT_ID: 2,
                PARAMS: {"move_mode": 1, "rate": 255},
            },
            (LONG_RELEASE, BUTTON_2): {COMMAND: COMMAND_STOP, ENDPOINT_ID: 2},
        }
    )
    .add_to_registry()
)
