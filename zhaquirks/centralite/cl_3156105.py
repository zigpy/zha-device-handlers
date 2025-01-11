"""Device handler for CentraLite 3156105."""

from typing import Any

from zigpy.profiles import zha
from zigpy.quirks import CustomCluster, CustomDevice
from zigpy.zcl.clusters.general import (
    Alarms,
    Basic,
    Groups,
    Identify,
    Ota,
    PowerConfiguration,
    Time,
)
from zigpy.zcl.clusters.hvac import (
    Fan,
    RunningMode,
    RunningState,
    Thermostat,
    UserInterface,
)

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)


class CustomThermostatCluster(CustomCluster, Thermostat):
    """Custom Thermostat cluster.

    With the system type set to "Heat Pump":

    System Mode | Fan Mode | Running? | `running_mode` | `running_state`
    ----------- | -------- | -------- | -------------- | ---------------
    Off         | Auto     | No       | Off (0)        | Heat (1)
    Heat        | Auto     | No       | Off (0)        | Heat (1)
    Heat        | Auto     | Yes      | Heat (4)       | Heat + Fan (5)
    Heat        | On       | No       | Off (0)        | Heat + Fan (5)
    Heat        | On       | Yes      | Heat (4)       | Heat + Fan (5)
    Cool        | Auto     | No       | Off (0)        | Heat (1)
    Cool        | Auto     | Yes      | Cool (3)       | Heat + Cool + Fan (7)
    Cool        | On       | No       | Off (0)        | Heat + Fan (5)
    Cool        | On       | Yes      | Cool (3)       | Heat + Cool + Fan (7)

    Note: The combination System Mode Off and Fan Mode On isn't supported.

    To fix this up,
    we correct the `running_state` based on the `running_mode`.
    The `running_mode` is the most recent value of `system_mode` that fits.

    """

    raw_running_mode: RunningMode
    corrected_running_mode: RunningMode
    raw_running_state: RunningState

    def __init__(self, *args, **kwargs):
        """Set up state."""
        super().__init__(*args, **kwargs)
        self.raw_running_mode = RunningMode.Off
        self.corrected_running_mode = RunningMode.Off
        self.raw_running_state = RunningState.Idle

    def _corrected_running_state(self):
        masked_running_state = self.raw_running_state & ~(
            RunningState.Heat_State_On | RunningState.Cool_State_On
        )
        if self.raw_running_mode == RunningMode.Off:
            corrected_running_state = masked_running_state
        elif self.raw_running_mode == RunningMode.Cool:
            corrected_running_state = masked_running_state | RunningState.Cool_State_On
        elif self.raw_running_mode == RunningMode.Heat:
            corrected_running_state = masked_running_state | RunningState.Heat_State_On
        else:
            raise RuntimeError("Unreachable!")

        return corrected_running_state

    def _update_attribute(self, attrid: int, value: Any) -> None:
        if attrid == self.AttributeDefs.running_state.id:
            assert isinstance(value, int)
            self.raw_running_state = value
            rs = self._corrected_running_state()
            super()._update_attribute(self.AttributeDefs.running_state.id, rs)
        elif attrid == self.AttributeDefs.running_mode.id:
            assert isinstance(value, int)
            self.raw_running_mode = value
            rs = self._corrected_running_state()
            super()._update_attribute(self.AttributeDefs.running_state.id, rs)
        elif attrid == self.AttributeDefs.system_mode.id:
            assert isinstance(value, int)
            if value in RunningMode:
                self.corrected_running_mode = value
                super()._update_attribute(self.AttributeDefs.running_mode.id, value)
            super()._update_attribute(attrid, value)
        else:
            super()._update_attribute(attrid, value)


class Centralite3156105(CustomDevice):
    """Custom device representing CentraLite 3156105."""

    signature = {
        MODELS_INFO: [("CentraLite Systems", "3156105")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.THERMOSTAT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Alarms.cluster_id,
                    Thermostat.cluster_id,
                    Fan.cluster_id,
                    UserInterface.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Time.cluster_id,
                    Ota.cluster_id,
                ],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.THERMOSTAT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Alarms.cluster_id,
                    CustomThermostatCluster,
                    Fan.cluster_id,
                    UserInterface.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Time.cluster_id,
                    Ota.cluster_id,
                ],
            }
        }
    }
