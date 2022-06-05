"""Tuya temp and humidity sensor with e-ink screen."""

import logging

from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
import zigpy.types as t
from zigpy.zcl.clusters.general import (
    Basic,
    Groups,
    Ota,
    Scenes,
    Time,
)
from zigpy.zcl.clusters.measurement import RelativeHumidity, TemperatureMeasurement
from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks import Bus, LocalDataCluster
from zhaquirks.ikea import PowerConfiguration2AAACluster
from zhaquirks.tuya import TuyaManufClusterAttributes

#### NOTES ####
# The data comes in as a string on cluster, if there is nothing set up you may see these lines in the logs:
# Unknown message (b'19830100a40102000400000118') on cluster 61184: unknown endpoint or cluster id: 'No cluster ID 0xef00 on (a4:c1:38:d0:18:8b:64:aa, 1)'
#                                          28.0 degrees
# Unknown message (b'19840100a5020200040000022c') on cluster 61184: unknown endpoint or cluster id: 'No cluster ID 0xef00 on (a4:c1:38:d0:18:8b:64:aa, 1)'
#                                          55.6% humid
# Unknown message (b'19850100a60402000400000064') on cluster 61184: unknown endpoint or cluster id: 'No cluster ID 0xef00 on (a4:c1:38:d0:18:8b:64:aa, 1)'
#                                          100% battery

# Constants that map to the string values in the previously `Unknown message` lines.
TUYA_TEMPERATURE_ATTR = 0x0201  # [0, 0, 0, 237] temperature in decidegree
TUYA_HUMIDITY_ATTR = 0x0202  # [0, 0, 2, 64] humidity
TUYA_BATTERY_ATTR = 0x0204  # [0, 0, 0, 100] battery

_LOGGER = logging.getLogger(__name__)


class TuyaTempHumidityDetectorCluster(TuyaManufClusterAttributes):
    """Manufacturer Specific Cluster of the TS0601 temp and humidity sensor with e-ink screen."""

    attributes = TuyaManufClusterAttributes.attributes.copy()
    attributes.update(
        {
            TUYA_TEMPERATURE_ATTR: ("temperature", t.uint32_t, True),
            TUYA_HUMIDITY_ATTR: ("humidity", t.uint32_t, True),
            TUYA_BATTERY_ATTR: ("battery", t.uint8_t, True),
        }
    )

    # For any attribute that comes in on the bus, inspect and redirect to the appropriate cluster
    def _update_attribute(self, attrid, value):
        super()._update_attribute(attrid, value)
        if attrid == TUYA_TEMPERATURE_ATTR:
            _LOGGER.debug("Raw temperature reported: %s", value)
            self.endpoint.device.temperature_bus.listener_event(
                "temperature_reported", value * 10  # decidegree to centidegree
            )
        elif attrid == TUYA_HUMIDITY_ATTR:
            _LOGGER.debug("Raw humidity reported: %s", value)
            self.endpoint.device.humidity_bus.listener_event(
                "humidity_reported", value * 10  # decipercent to centipercent
            )
        elif attrid == TUYA_BATTERY_ATTR:
            _LOGGER.debug("Raw battery reported: %s", value)
            self.endpoint.device.battery_bus.listener_event(
                "battery_reported", value  # whole percentage
            )
        else:
            _LOGGER.warning(
                "[0x%04x:%s:0x%04x] unhandled attribute: 0x%04x",
                self.endpoint.device.nwk,
                self.endpoint.endpoint_id,
                self.cluster_id,
                attrid,
                value,
            )


class TuyaTemperatureMeasurement(LocalDataCluster, TemperatureMeasurement):
    """Temperature cluster acting from events from temperature bus."""

    cluster_id = TemperatureMeasurement.cluster_id
    ATTR_ID = 0x0000  # measured_value

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self.endpoint.device.temperature_bus.add_listener(self)

    def temperature_reported(self, value):
        _LOGGER.debug("Temperature update: %s", value)
        self._update_attribute(self.ATTR_ID, value)


class TuyaRelativeHumidity(LocalDataCluster, RelativeHumidity):
    """Humidity cluster acting from events from humidity bus."""

    cluster_id = RelativeHumidity.cluster_id
    ATTR_ID = 0x0000  # measured_value

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self.endpoint.device.humidity_bus.add_listener(self)

    def humidity_reported(self, value):
        _LOGGER.debug("Humidity update: %s", value)
        self._update_attribute(self.ATTR_ID, value)


class TuyaPower(PowerConfiguration2AAACluster):
    """Battery Power cluster acting from events from power bus."""

    ATTR_ID = 0x0021  # battery_percentage_remaining

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self.endpoint.device.battery_bus.add_listener(self)

    def battery_reported(self, value):
        _LOGGER.debug("Battery update: %s", value)
        self._update_attribute(self.ATTR_ID, value)


class TuyaTempHumidity(CustomDevice):
    """Custom device representing tuya temp and humidity sensor with e-ink screen."""

    def __init__(self, *args, **kwargs):
        """Init device."""
        self.temperature_bus = Bus()
        self.humidity_bus = Bus()
        self.battery_bus = Bus()
        super().__init__(*args, **kwargs)

    signature = {
        # <SimpleDescriptor endpoint=1, profile=260, device_type=81
        # device_version=1
        # input_clusters=[4, 5, 61184, 0]
        # output_clusters=[25, 10]>
        MODELS_INFO: [("_TZE200_bjawzodf", "TS0601")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaTempHumidityDetectorCluster.cluster_id,
                    Basic.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id, Time.cluster_id],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.TEMPERATURE_SENSOR,
                INPUT_CLUSTERS: [
                    TuyaTempHumidityDetectorCluster,  # Single bus for temp, humidity, and battery
                    Basic.cluster_id,
                    TuyaTemperatureMeasurement,
                    TuyaRelativeHumidity,
                    TuyaPower,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id, Time.cluster_id],
            }
        },
    }
