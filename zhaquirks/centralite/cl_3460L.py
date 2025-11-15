"""Device handler for centralite 3460L."""

# pylint disable=C0103
from zigpy.quirks.v2 import QuirkBuilder

from zhaquirks import PowerConfigurationCluster
from zhaquirks.centralite import CENTRALITE
from zhaquirks.const import (
    BUTTON_1,
    COMMAND,
    COMMAND_OFF,
    COMMAND_ON,
    SHORT_PRESS,
    SHORT_RELEASE,
)


class CustomPowerConfigurationCluster(PowerConfigurationCluster):
    """Custom PowerConfigurationCluster."""

    MIN_VOLTS = 2.1
    MAX_VOLTS = 3.0


(
    QuirkBuilder(CENTRALITE, "3460-L")
    .replaces(CustomPowerConfigurationCluster, endpoint_id=1)
    .device_automation_triggers(
        {
            (SHORT_PRESS, BUTTON_1): {COMMAND: COMMAND_ON},
            (SHORT_RELEASE, BUTTON_1): {COMMAND: COMMAND_OFF},
        }
    )
    .add_to_registry()
)
