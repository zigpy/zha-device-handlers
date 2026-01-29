"""Device handler for centralite 3450L."""

# pylint disable=C0103
from zigpy.quirks.v2 import QuirkBuilder

from zhaquirks import PowerConfigurationCluster
from zhaquirks.centralite import CENTRALITE
from zhaquirks.const import (
    BUTTON_1,
    BUTTON_2,
    BUTTON_3,
    BUTTON_4,
    COMMAND,
    COMMAND_PRESS,
    ENDPOINT_ID,
    SHORT_PRESS,
)


class CustomPowerConfigurationCluster(PowerConfigurationCluster):
    """Custom PowerConfigurationCluster."""

    MIN_VOLTS = 2.1
    MAX_VOLTS = 3.0


(
    QuirkBuilder(CENTRALITE, "3450-L")
    .applies_to(CENTRALITE, "3450-L2")
    .replaces(CustomPowerConfigurationCluster, endpoint_id=1)
    .device_automation_triggers(
        {
            (SHORT_PRESS, BUTTON_1): {COMMAND: COMMAND_PRESS, ENDPOINT_ID: 1},
            (SHORT_PRESS, BUTTON_2): {COMMAND: COMMAND_PRESS, ENDPOINT_ID: 2},
            (SHORT_PRESS, BUTTON_3): {COMMAND: COMMAND_PRESS, ENDPOINT_ID: 3},
            (SHORT_PRESS, BUTTON_4): {COMMAND: COMMAND_PRESS, ENDPOINT_ID: 4},
        }
    )
    .add_to_registry()
)
