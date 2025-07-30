"""Third Reality button devices."""

from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl.clusters.general import Basic, LevelControl, MultistateInput, OnOff, Ota

from zhaquirks import CustomCluster, PowerConfigurationCluster
from zhaquirks.const import (
    COMMAND,
    COMMAND_DOUBLE,
    COMMAND_HOLD,
    COMMAND_RELEASE,
    COMMAND_SINGLE,
    DEVICE_TYPE,
    DOUBLE_PRESS,
    ENDPOINTS,
    INPUT_CLUSTERS,
    LONG_PRESS,
    LONG_RELEASE,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
    SHORT_PRESS,
    SKIP_CONFIGURATION,
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
    .replaces_endpoint(endpoint_id=1, profile_id=0x0104, device_type=zha.DeviceType.REMOTE_CONTROL)
    .replaces(replacement_cluster_class=CustomPowerConfigurationCluster, cluster_id=CustomPowerConfigurationCluster.cluster_id)
    .replaces(replacement_cluster_class=MultistateInputCluster, cluster_id=MultistateInput.cluster_id)
    .skip_configuration()
    .device_automation_triggers({
        (DOUBLE_PRESS, DOUBLE_PRESS): {COMMAND: COMMAND_DOUBLE},
        (SHORT_PRESS, SHORT_PRESS): {COMMAND: COMMAND_SINGLE},
        (LONG_PRESS, LONG_PRESS): {COMMAND: COMMAND_HOLD},
        (LONG_RELEASE, LONG_RELEASE): {COMMAND: COMMAND_RELEASE},
    })
    .add_to_registry()
)
