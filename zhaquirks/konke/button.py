"""Konke Button Remote."""

from zigpy.quirks.v2 import QuirkBuilder

from zhaquirks import PowerConfigurationCluster
from zhaquirks.const import (
    COMMAND,
    COMMAND_DOUBLE,
    COMMAND_HOLD,
    COMMAND_SINGLE,
    DOUBLE_PRESS,
    LONG_PRESS,
    SHORT_PRESS,
)
from zhaquirks.konke import KONKE, KonkeOnOffCluster

(
    QuirkBuilder(KONKE, "3AFE280100510001")
    .applies_to(KONKE, "3AFE170100510001")
    .replaces(PowerConfigurationCluster, endpoint_id=1)
    .replaces(KonkeOnOffCluster, endpoint_id=1)
    .device_automation_triggers(
        {
            (DOUBLE_PRESS, DOUBLE_PRESS): {COMMAND: COMMAND_DOUBLE},
            (SHORT_PRESS, SHORT_PRESS): {COMMAND: COMMAND_SINGLE},
            (LONG_PRESS, LONG_PRESS): {COMMAND: COMMAND_HOLD},
        }
    )
    .add_to_registry()
)
