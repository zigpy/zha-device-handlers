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

SAMJIN_BUTTON_TRIGGERS = {
    (DOUBLE_PRESS, DOUBLE_PRESS): {COMMAND: COMMAND_BUTTON_DOUBLE},
    (SHORT_PRESS, SHORT_PRESS): {COMMAND: COMMAND_BUTTON_SINGLE},
    (LONG_PRESS, LONG_PRESS): {COMMAND: COMMAND_BUTTON_HOLD},
}

(
    QuirkBuilder(SAMJIN, BUTTON)
    .replaces(replacement_cluster_class=SamjinIASCluster, cluster_id=IasZone.cluster_id)
    .device_automation_triggers(SAMJIN_BUTTON_TRIGGERS)
    .add_to_registry()
)


# Note: SamjinButton2 variation without Diagnostic cluster is handled by the same v2 quirk above
# since v2 API only replaces the IasZone cluster, other differences are handled automatically
