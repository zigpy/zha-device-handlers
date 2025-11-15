"""Samjin button device."""

from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl.clusters.security import IasZone

from zhaquirks.const import (
    BUTTON,
    COMMAND,
    COMMAND_BUTTON_DOUBLE,
    COMMAND_BUTTON_HOLD,
    COMMAND_BUTTON_SINGLE,
    DOUBLE_PRESS,
    LONG_PRESS,
    SHORT_PRESS,
)
from zhaquirks.samjin import SAMJIN, SamjinIASCluster

(
    QuirkBuilder(SAMJIN, BUTTON)
    .replaces(SamjinIASCluster, cluster_id=IasZone.cluster_id, endpoint_id=1)
    .device_automation_triggers(
        {
            (DOUBLE_PRESS, DOUBLE_PRESS): {COMMAND: COMMAND_BUTTON_DOUBLE},
            (SHORT_PRESS, SHORT_PRESS): {COMMAND: COMMAND_BUTTON_SINGLE},
            (LONG_PRESS, LONG_PRESS): {COMMAND: COMMAND_BUTTON_HOLD},
        }
    )
    .add_to_registry()
)
