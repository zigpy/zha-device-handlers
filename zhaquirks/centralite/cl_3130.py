"""Device handler for centralite 3130."""

from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl.clusters.measurement import TemperatureMeasurement

from zhaquirks import PowerConfigurationCluster
from zhaquirks.centralite import CENTRALITE
from zhaquirks.const import (
    COMMAND,
    COMMAND_MOVE,
    COMMAND_MOVE_ON_OFF,
    COMMAND_OFF,
    COMMAND_ON,
    DIM_DOWN,
    DIM_UP,
    SHORT_PRESS,
    TURN_OFF,
    TURN_ON,
)
from zhaquirks.osram import OSRAM


class CustomPowerConfigurationCluster(PowerConfigurationCluster):
    """Custom PowerConfigurationCluster."""

    MIN_VOLTS = 2.1
    MAX_VOLTS = 3.0


(
    QuirkBuilder(OSRAM, "LIGHTIFY Dimming Switch")
    .applies_to(CENTRALITE, "3130")
    .removes(TemperatureMeasurement, endpoint_id=1)
    .replaces(CustomPowerConfigurationCluster, endpoint_id=1)
    .device_automation_triggers(
        {
            (SHORT_PRESS, TURN_ON): {COMMAND: COMMAND_ON},
            (SHORT_PRESS, TURN_OFF): {COMMAND: COMMAND_OFF},
            (SHORT_PRESS, DIM_UP): {COMMAND: COMMAND_MOVE_ON_OFF},
            (SHORT_PRESS, DIM_DOWN): {COMMAND: COMMAND_MOVE},
        }
    )
    .add_to_registry()
)
