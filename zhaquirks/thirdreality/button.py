"""Third Reality button devices."""

from zigpy.profiles import zha
from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl.clusters.general import MultistateInput

from zhaquirks import CustomCluster, PowerConfigurationCluster
from zhaquirks.const import (
    COMMAND,
    COMMAND_DOUBLE,
    COMMAND_HOLD,
    COMMAND_RELEASE,
    COMMAND_SINGLE,
    DOUBLE_PRESS,
    LONG_PRESS,
    LONG_RELEASE,
    SHORT_PRESS,
    VALUE,
    ZHA_SEND_EVENT,
)
from zhaquirks.thirdreality import THIRD_REALITY


class CustomPowerConfigurationCluster(PowerConfigurationCluster):
    """Custom PowerConfigurationCluster."""

    MIN_VOLTS = 2.1
    MAX_VOLTS = 3.0


MOVEMENT_TYPE = {
    0: COMMAND_HOLD,
    1: COMMAND_SINGLE,
    2: COMMAND_DOUBLE,
    255: COMMAND_RELEASE,
}


class MultistateInputCluster(CustomCluster, MultistateInput):
    """Multistate input cluster."""

    def __init__(self, *args, **kwargs):
        """Init."""
        self._current_state = {}
        super().__init__(*args, **kwargs)

    def _update_attribute(self, attrid, value):
        super()._update_attribute(attrid, value)
        if attrid == 0x0055:
            self._current_state[0x0055] = action = MOVEMENT_TYPE.get(value)
            event_args = {VALUE: value}
            if action is not None:
                self.listener_event(ZHA_SEND_EVENT, action, event_args)

            # show something in the sensor in HA
            super()._update_attribute(0, action)


(
    QuirkBuilder(THIRD_REALITY, "3RSB22BZ")
    .skip_configuration()
    .replaces_endpoint(endpoint_id=1, device_type=zha.DeviceType.REMOTE_CONTROL)
    .replaces(CustomPowerConfigurationCluster, endpoint_id=1)
    .replaces(MultistateInputCluster, endpoint_id=1)
    .device_automation_triggers(
        {
            (DOUBLE_PRESS, DOUBLE_PRESS): {COMMAND: COMMAND_DOUBLE},
            (SHORT_PRESS, SHORT_PRESS): {COMMAND: COMMAND_SINGLE},
            (LONG_PRESS, LONG_PRESS): {COMMAND: COMMAND_HOLD},
            (LONG_RELEASE, LONG_RELEASE): {COMMAND: COMMAND_RELEASE},
        }
    )
    .add_to_registry()
)
