"""Module for Legrand wireless radiant switch."""

from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl.clusters.general import BinaryInput

from zhaquirks.const import (
    BUTTON,
    COMMAND,
    COMMAND_MOVE,
    COMMAND_OFF,
    COMMAND_ON,
    COMMAND_STOP,
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
