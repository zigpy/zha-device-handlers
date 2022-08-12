"""Tuya TS201 temperature, humidity and optional illumination sensors."""

from zigpy.profiles import zha
from zigpy.profiles.zha import DeviceType
from zigpy.quirks import CustomCluster, CustomDevice
import zigpy.types as t
from zigpy.zcl.clusters.general import Basic, Identify, Ota, PowerConfiguration, Time
from zigpy.zcl.clusters.measurement import (
    IlluminanceMeasurement,
    RelativeHumidity,
    TemperatureMeasurement,
)
from zigpy.zdo.types import NodeDescriptor

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    NODE_DESCRIPTOR,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)


class ValueAlarm(t.enum8):
    """Temperature and humidity alarm values."""

    ALARM_OFF = 0x02
    MAX_ALARM_ON = 0x01
    MIN_ALARM_ON = 0x00


class TuyaTemperatureHumidityAlarmCluster(CustomCluster):
    """Tuya temperature and humidity alarm cluster (0xE002)."""

    name = "Tuya Temperature and Humidity Alarm Cluster"
    cluster_id = 0xE002

    attributes = {
        # Alarm settings
        0xD00A: ("alarm_temperature_max", t.uint16_t, True),
        0xD00B: ("alarm_temperature_min", t.uint16_t, True),
        0xD00C: ("alarm_humidity_max", t.uint16_t, True),
        0xD00E: ("alarm_humidity_min", t.uint16_t, True),
        # Alarm information
        0xD00F: ("alarm_humidity", ValueAlarm, True),
        0xD006: ("temperature_humidity", ValueAlarm, True),
        # Unknown
        0xD010: ("unknown", t.uint8_t, True),
    }


class NeoTemperatureHumidtyIlluminanceSensor(CustomDevice):
    """Neo temperature, humidity and illumination sensor."""

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
                    TuyaTemperatureHumidityAlarmCluster.cluster_id,
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
                    TuyaTemperatureHumidityAlarmCluster,
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


class ZemismartTemperatureHumidtySensor(CustomDevice):
    """Zemismart temperature and humidity sensor."""

    signature = {
        #  <SimpleDescriptor endpoint=1 profile=260 device_type=770
        # device_version=1
        # input_clusters=[0, 1, 3, 1029, 1026, 61183]
        # output_clusters=[3, 25]>
        MODELS_INFO: [("_TZ3000_lfa05ajd", "TS0201")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.TEMPERATURE_SENSOR,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    RelativeHumidity.cluster_id,
                    TemperatureMeasurement.cluster_id,
                    0xEEFF,  # Unknown
                ],
                OUTPUT_CLUSTERS: [Identify.cluster_id, Ota.cluster_id],
            }
        },
    }

    replacement = {
        NODE_DESCRIPTOR: NodeDescriptor(
            0x02,
            0x40,
            0x80,
            0x1037,
            0x7F,
            0x0064,
            0x2C00,
            0x0064,
            0x00,  # Forcing capability 0x80 instead of 0x84 so AC Power = false
        ),
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.TEMPERATURE_SENSOR,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    RelativeHumidity.cluster_id,
                    TemperatureMeasurement.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Identify.cluster_id, Ota.cluster_id],
            }
        },
    }


class RelativeHumidityX10(CustomCluster, RelativeHumidity):
    """Handles invalid humidity values."""

    def _update_attribute(self, attrid, value):
        # x10 factor in measured_value`(attrid=0)
        if attrid == 0:
            value = value * 10
        super()._update_attribute(attrid, value)


class MoesTemperatureHumidtySensorWithScreen(CustomDevice):
    """Moes temperature and humidity sensor with screen."""

    signature = {
        #  <SimpleDescriptor endpoint=1, profile=260, device_type="0x0302"
        #  input_clusters=["0x0000", "0x0001", "0x0003", "0x0402", "0x0405", "0xe002"]
        #  output_clusters=["0x0003", "0x000a", "0x0019"]>
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
                    TuyaTemperatureHumidityAlarmCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
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
                    Identify.cluster_id,
                    TemperatureMeasurement.cluster_id,
                    RelativeHumidityX10,
                    TuyaTemperatureHumidityAlarmCluster,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Time.cluster_id,
                    Ota.cluster_id,
                ],
            },
        },
    }
