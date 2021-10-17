"""Neo Tuya Temperature, Humidity and Illumination Sensor."""

from zigpy.profiles import zha
from zigpy.profiles.zha import DeviceType
from zigpy.quirks import CustomCluster, CustomDevice
import zigpy.types as t
from zigpy.zcl.clusters.general import Basic, Ota, PowerConfiguration, Time
from zigpy.zcl.clusters.measurement import (
    IlluminanceMeasurement,
    RelativeHumidity,
    TemperatureMeasurement,
)

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)


class ValueAlarm(t.enum8):
    """Temperature and Humidity alarm values."""

    ALARM_OFF = 0x02
    MAX_ALARM_ON = 0x01
    MIN_ALARM_ON = 0x00


class NeoTemperatureHumidityAlarmCluster(CustomCluster):
    """Neo Temperature and Humidity Alarm Cluster (0xE002)."""

    name = "Neo Temperature and Humidity Alarm Cluster"
    cluster_id = 0xE002

    manufacturer_attributes = {
        # Alarm settings
        0xD00A: ("alarm_temperature_man", t.uint16_t),
        0xD00B: ("alarm_temperature_min", t.uint16_t),
        0xD00C: ("alarm_humidity_max", t.uint16_t),
        0xD00E: ("alarm_humidity_min", t.uint16_t),
        # Alarm information
        0xD00F: ("alarm_humidity", ValueAlarm),
        0xD006: ("temperature_humidity", ValueAlarm),
        # Unknown
        0xD010: {"unknown", t.uint8_t},
    }


class TemperatureHumidtyIlluminanceSensor(CustomDevice):
    """Neo Tuya Temperature, Humidity and Illumination Sensor."""

    signature = {
        #  <SimpleDescriptor endpoint=1, profile=260, device_type=262
        #  device_version=1
        #  input_clusters=[0, 1, 1024, 57346]
        #  output_clusters=[25, 10]>
        MODELS_INFO: [("_TZ3000_qaaysllp", "TS0201")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: DeviceType.LIGHT_SENSOR,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    IlluminanceMeasurement.cluster_id,
                    NeoTemperatureHumidityAlarmCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Time.cluster_id,
                    Ota.cluster_id,
                ],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    IlluminanceMeasurement.cluster_id,
                    NeoTemperatureHumidityAlarmCluster,
                ],
                OUTPUT_CLUSTERS: [
                    Time.cluster_id,
                    Ota.cluster_id,
                ],
            },
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: DeviceType.TEMPERATURE_SENSOR,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    TemperatureMeasurement.cluster_id,
                    RelativeHumidity.cluster_id,
                ],
            },
        },
    }
