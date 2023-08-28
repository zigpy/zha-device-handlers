"""Sonoff SNZB-02 temperature/humidity sensor."""
from zigpy.profiles import zha
from zigpy.profiles.zha import DeviceType
from zigpy.quirks import CustomCluster, CustomDevice
from zigpy.zcl.clusters.general import Basic, Identify, PowerConfiguration
from zigpy.zcl.clusters.measurement import RelativeHumidity, TemperatureMeasurement

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)


class SonoffRelativeHumidityCluster(CustomCluster, RelativeHumidity):
    """Fixes too high humidity values reported by Sonoff SNZB-02."""

    def _update_attribute(self, attrid, value):
        # drop values above and below documented range for this sensor
        # and apply a 6% correction
        if attrid == 0 and (0 <= value <= 9999):
            super()._update_attribute(attrid, value * 0.94)


class TemperatureHumidtySensor(CustomDevice):
    """Sonoff SNZB-02 temperature/humidity sensor."""

    signature = {
        # <SimpleDescriptor endpoint=1 profile=260 device_type="0x0302"
        # device_version=1
        # input_clusters=["0x0000", "0x0001", "0x0003", "0x0402", "0x0405"]
        # output_clusters=["0x0003"]>
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: DeviceType.TEMPERATURE_SENSOR,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    TemperatureMeasurement.cluster_id,
                    RelativeHumidity.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                ],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    TemperatureMeasurement.cluster_id,
                    SonoffRelativeHumidityCluster,
                ],
                OUTPUT_CLUSTERS: [Identify.cluster_id],
            }
        }
    }
