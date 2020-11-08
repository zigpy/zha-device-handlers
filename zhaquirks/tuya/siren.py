"""Map from manufacturer to standard clusters for the NEO Siren device."""
import logging
from typing import Optional, Union

from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import Basic, Identify, OnOff, Ota
from zigpy.zcl.clusters.measurement import RelativeHumidity, TemperatureMeasurement

from . import TuyaManufClusterAttributes
from .. import Bus, LocalDataCluster
from ..const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)

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

    def _update_attribute(self, attrid, value):
        super()._update_attribute(attrid, value)
        if attrid == TUYA_TEMPERATURE_ATTR:
            self.endpoint.device.temperature_bus.listener_event(
                "temperature_reported", value * 10  # decidegree to centidegree
            )
        elif attrid == TUYA_HUMIDITY_ATTR:
            self.endpoint.device.humidity_bus.listener_event(
                "humidity_reported", value * 100  # whole percentage to 1/1000th
            )
        elif attrid == TUYA_ALARM_ATTR:
            self.endpoint.device.switch_bus.listener_event(
                "switch_event", value  # boolean 1=on / 0=off
            )


class TuyaSirenOnOff(LocalDataCluster, OnOff):
    """Tuya On/Off cluster for siren device."""

    ATTR_ID = 0

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self.endpoint.device.switch_bus.add_listener(self)

    def switch_event(self, state):
        """Switch event."""
        self._update_attribute(self.ATTR_ID, state)

    def command(
        self,
        command_id: Union[foundation.Command, int, t.uint8_t],
        *args,
        manufacturer: Optional[Union[int, t.uint16_t]] = None,
        expect_reply: bool = True,
        tsn: Optional[Union[int, t.uint8_t]] = None,
    ):
        """Override the default command and defer to the alarm attribute."""

        if command_id in (0x0000, 0x0001):
            return self.endpoint.tuya_manufacturer.write_attributes(
                {TUYA_ALARM_ATTR: command_id}, manufacturer=manufacturer
            )

        return foundation.Status.UNSUP_CLUSTER_COMMAND


class TuyaTemperatureMeasurement(LocalDataCluster, TemperatureMeasurement):
    """Temperature cluster acting from events from temperature bus."""

    cluster_id = TemperatureMeasurement.cluster_id
    ATTR_ID = 0

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self.endpoint.device.temperature_bus.add_listener(self)

    def temperature_reported(self, value):
        """Temperature reported."""
        self._update_attribute(self.ATTR_ID, value)


class TuyaRelativeHumidity(LocalDataCluster, RelativeHumidity):
    """Humidity cluster acting from events from humidity bus."""

    cluster_id = RelativeHumidity.cluster_id
    ATTR_ID = 0

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self.endpoint.device.humidity_bus.add_listener(self)

    def humidity_reported(self, value):
        """Humidity reported."""
        self._update_attribute(self.ATTR_ID, value)


class TuyaSiren(CustomDevice):
    """NEO Tuya Siren and humidity/temperature sensor."""

    def __init__(self, *args, **kwargs):
        """Init device."""
        self.temperature_bus = Bus()
        self.humidity_bus = Bus()
        self.switch_bus = Bus()
        super().__init__(*args, **kwargs)

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
                    TuyaTemperatureMeasurement,
                    TuyaRelativeHumidity,
                    TuyaSirenOnOff,
                ],
                OUTPUT_CLUSTERS: [Identify.cluster_id, Ota.cluster_id],
            }
        }
    }
