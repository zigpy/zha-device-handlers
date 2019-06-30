"""Keen Home temperature/humidity/pressure sensor."""
from zigpy.quirks import CustomDevice, CustomCluster
from zigpy.profiles import zha
from zigpy.profiles.zha import DeviceType
from zigpy.zcl.clusters.general import (
    Basic, Identify, PowerConfiguration, PollControl, Groups, Scenes, Ota)
from zigpy.zcl.clusters.measurement import (
    TemperatureMeasurement, RelativeHumidity, PressureMeasurement)


class PressureMeasurementCluster(CustomCluster, PressureMeasurement):
    """Custom cluster representing Keen Home's pressure measurement."""

    cluster_id = PressureMeasurement.cluster_id

    KEEN_MEASURED_VALUE_ATTR = 0x0020
    MEASURED_VALUE_ATTR = 0x0000

    def _update_attribute(self, attrid, value):
        super()._update_attribute(attrid, value)
        if attrid == self.KEEN_MEASURED_VALUE_ATTR:
            value = value / 1000.0
            super()._update_attribute(self.MEASURED_VALUE_ATTR, value)


class TemperatureHumidtyPressureSensor(CustomDevice):
    """Keen Home temperature/humidity/pressure sensor."""

    signature = {
        # <SimpleDescriptor endpoint=1 profile=260 device_type=770
        # device_version=1
        # input_clusters=[0, 3, 1, 32]
        # output_clusters=[0, 4, 3, 5, 25, 1026, 1029, 1027, 32]>
        'models_info': [
            ('LUMI', 'RS-THP-MP-1.0')
        ],
        'endpoints': {
            1: {
                'profile_id': zha.PROFILE_ID,
                'device_type': DeviceType.TEMPERATURE_SENSOR,
                'input_clusters': [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    PowerConfiguration.cluster_id,
                    PollControl.cluster_id
                ],
                'output_clusters': [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Identify.cluster_id,
                    Scenes.cluster_id,
                    Ota.cluster_id,
                    TemperatureMeasurement.cluster_id,
                    RelativeHumidity.cluster_id,
                    PressureMeasurement.cluster_id,
                    PollControl.cluster_id
                ],
            }
        }
    }

    replacement = {
        'endpoints': {
            1: {
                'input_clusters': [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    PowerConfiguration.cluster_id,
                    RelativeHumidity.cluster_id,
                    TemperatureMeasurement.cluster_id,
                    PollControl.cluster_id,
                    PressureMeasurementCluster
                ],
                'output_clusters': [
                    Basic.cluster_id,
                    Groups.cluster_id
                ]
            }
        }
    }
