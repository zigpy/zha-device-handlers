"""Manufacturer Specific Cluster of the NEO Siren device."""
import logging

from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
from zigpy.zcl.clusters.general import Basic, Identify, Ota
import zigpy.types as t

from ..const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)

from . import TuyaManufClusterAttributes

TUYA_ALARM_ATTR = 0x0168  # [0]/[1] Alarm!
TUYA_TEMP_ALARM_ATTR = 0x0171  # [0]/[1] Disable/Enable alarm by temperature
TUYA_HUMID_ALARM_ATTR = 0x0172  # [0]/[1] Disable/Enable alarm by humidity
TUYA_ALARM_DURATION_ATTR = 0x0267  # [0,0,0,10] duration alarm in second
TUYA_TEMPERATURE_ATTR = 0x0269  # [0,0,0,240] temperature in decidegree
TUYA_HUMIDITY_ATTR = 0x026A  # [0,0,0,36] humidity
TUYA_ALARM_MIN_TEMP_ATTR = 0x026B  # [0,0,0,18] min alarm temperature threshold
TUYA_ALARM_MAX_TEMP_ATTR = 0x026C  # [0,0,0,18] max alarm temperature threshold
TUYA_ALARM_MIN_HUMID_ATTR = 0x026D  # [0,0,0,18] min alarm humidity threshold
TUYA_ALARM_MAX_HUMID_ATTR = 0x026E  # [0,0,0,18] max alarm humidity threshold
TUYA_MELODY_ATTR = 0x0466  # [5] Melody
TUYA_VOLUME_ATTR = 0x0474  # [0]/[1]/[2] Volume 0-max, 2-low

_LOGGER = logging.getLogger(__name__)


class TuyaManufClusterSiren(TuyaManufClusterAttributes):
    """Manufacturer Specific Cluster of the NEO Siren device."""

    manufacturer_attributes = {
        TUYA_ALARM_ATTR: ("alarm", t.uint8_t),
        TUYA_TEMP_ALARM_ATTR: ("enable_temperature_alarm", t.uint8_t),
        TUYA_HUMID_ALARM_ATTR: ("enable_humidity_alarm", t.uint8_t),
        TUYA_ALARM_DURATION_ATTR: ("alarm_duration", t.uint32_t),
        TUYA_TEMPERATURE_ATTR: ("temperature", t.uint32_t),
        TUYA_HUMIDITY_ATTR: ("humidity", t.uint32_t),
        TUYA_ALARM_MIN_TEMP_ATTR: ("alarm_temperature_min", t.uint32_t),
        TUYA_ALARM_MAX_TEMP_ATTR: ("alarm_temperature_max", t.uint32_t),
        TUYA_ALARM_MIN_HUMID_ATTR: ("alarm_humidity_min", t.uint32_t),
        TUYA_ALARM_MAX_HUMID_ATTR: ("alarm_humidity_max", t.uint32_t),
        TUYA_MELODY_ATTR: ("melody", t.uint8_t),
        TUYA_VOLUME_ATTR: ("volume", t.uint8_t),
    }


class TuyaSiren(CustomDevice):
    """NEO Tuya Siren and humidity/temperature sensor."""

    signature = {
        #  endpoint=1 profile=260 device_type=0 device_version=0 input_clusters=[0, 3]
        #  output_clusters=[3, 25]>
        MODELS_INFO: [("_TYST11_d0yu2xgi", "0yu2xgi")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [Basic.cluster_id, Identify.cluster_id],
                OUTPUT_CLUSTERS: [Identify.cluster_id, Ota.cluster_id],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.IAS_WARNING_DEVICE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    TuyaManufClusterSiren,
                ],
                OUTPUT_CLUSTERS: [Identify.cluster_id, Ota.cluster_id],
            }
        }
    }
