"""Device handler for LUMI lumi.plug."""
from zigpy.profiles import zha
from zigpy.zcl.clusters.general import (
    Basic,
    PowerConfiguration,
    DeviceTemperature,
    Identify,
    Groups,
    Scenes,
    OnOff,
    Time,
    AnalogInput,
    BinaryOutput,
    Ota,
)
from zigpy.quirks import CustomDevice
from zhaquirks import CustomCluster

STATUS_TYPE_ATTR = 0x0055  # decimal = 85
CONST_POWER = "power"


class LUMIlumiplug(CustomDevice):
    """Custom device representing LUMI lumi.plug."""

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)

    class AnalogInputCluster(CustomCluster, AnalogInput):
        """Analog input cluster."""

        cluster_id = AnalogInput.cluster_id

        def __init__(self, *args, **kwargs):
            """Init."""
            self._current_state = {}
            super().__init__(*args, **kwargs)

        def _update_attribute(self, attrid, value):
            super()._update_attribute(attrid, value)
            if attrid == STATUS_TYPE_ATTR:
                if value:
                    self._current_state[STATUS_TYPE_ATTR] = CONST_POWER
                # show something in the sensor in HA
                super()._update_attribute(0, "{}".format(round(float(value), 2)))
                if (
                    STATUS_TYPE_ATTR in self._current_state
                    and self._current_state[STATUS_TYPE_ATTR] is not None
                ):
                    self.listener_event(
                        "zha_send_event",
                        self,
                        self._current_state[STATUS_TYPE_ATTR],
                        {"power": value},
                    )

    signature = {
        #  <SimpleDescriptor endpoint=1 profile=260 device_type=81
        #  device_version=1
        #  input_clusters=[0, 1, 2, 3, 4, 5, 6, 10, 16]
        #  output_clusters=[10, 25]>
        1: {
            "profile_id": zha.PROFILE_ID,
            "device_type": zha.DeviceType.SMART_PLUG,
            "input_clusters": [
                Basic.cluster_id,
                PowerConfiguration.cluster_id,
                DeviceTemperature.cluster_id,
                Identify.cluster_id,
                Groups.cluster_id,
                Scenes.cluster_id,
                OnOff.cluster_id,
                Time.cluster_id,
                BinaryOutput.cluster_id,
            ],
            "output_clusters": [Time.cluster_id, Ota.cluster_id],
        },
        #  <SimpleDescriptor endpoint=2 profile=260 device_type=9
        #  device_version=1
        #  input_clusters=[12]
        #  output_clusters=[4, 12]>
        2: {
            "profile_id": zha.PROFILE_ID,
            "device_type": zha.DeviceType.MAIN_POWER_OUTLET,
            "input_clusters": [AnalogInput.cluster_id],
            "output_clusters": [Groups.cluster_id, AnalogInput.cluster_id],
        },
        #  <SimpleDescriptor endpoint=3 profile=260 device_type=83
        #  device_version=1
        #  input_clusters=[12]
        #  output_clusters=[12]>
        3: {
            "profile_id": zha.PROFILE_ID,
            "device_type": zha.DeviceType.METER_INTERFACE,
            "input_clusters": [AnalogInput.cluster_id],
            "output_clusters": [AnalogInput.cluster_id],
        },
    }

    replacement = {
        "endpoints": {
            1: {
                "manufacturer": "LUMI",
                "model": "lumi.plug",
                "profile_id": zha.PROFILE_ID,
                "device_type": zha.DeviceType.SMART_PLUG,
                "input_clusters": [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    DeviceTemperature.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    Time.cluster_id,
                    BinaryOutput.cluster_id,
                ],
                "output_clusters": [Time.cluster_id, Ota.cluster_id],
            },
            2: {
                "manufacturer": "LUMI",
                "model": "lumi.plug",
                "profile_id": zha.PROFILE_ID,
                "device_type": zha.DeviceType.MAIN_POWER_OUTLET,
                "input_clusters": [AnalogInputCluster],
                "output_clusters": [Groups.cluster_id, AnalogInput.cluster_id],
            },
            3: {
                "manufacturer": "LUMI",
                "model": "lumi.plug",
                "profile_id": zha.PROFILE_ID,
                "device_type": zha.DeviceType.METER_INTERFACE,
                "input_clusters": [AnalogInputCluster],
                "output_clusters": [AnalogInput.cluster_id],
            },
        }
    }
