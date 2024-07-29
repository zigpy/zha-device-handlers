"""Develco Air Quality Sensor."""

import logging

from zigpy.profiles import zha
from zigpy.quirks import CustomCluster, CustomDevice
import zigpy.types as t
from zigpy.zcl.clusters.general import (
    Basic,
    Identify,
    OnOff,
    Ota,
    PollControl,
    PowerConfiguration,
    Scenes,
    Time,
)
from zigpy.zcl.clusters.measurement import RelativeHumidity, TemperatureMeasurement

from zhaquirks import Bus, LocalDataCluster
from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.develco import DEVELCO, DevelcoPowerConfiguration

MANUFACTURER = 0x1015
VOC_MEASURED_VALUE = 0x0000
VOC_MIN_MEASURED_VALUE = 0x0001
VOC_MAX_MEASURED_VALUE = 0x0002
VOC_RESOLUTION = 0x0003

VOC_REPORTED = "voc_reported"
MIN_VOC_REPORTED = "min_voc_reported"
MAX_VOC_REPORTED = "max_voc_reported"
VOC_RESOLUTION_REPORTED = "voc_resolution_reported"

_LOGGER = logging.getLogger(__name__)


class DevelcoVOCMeasurement(CustomCluster):
    """Input Cluster to route manufacturer specific VOC cluster to actual VOC cluster."""

    cluster_id = 0xFC03
    name = "VOC Level"
    ep_attribute = "voc_level"
    attributes = {
        VOC_MEASURED_VALUE: ("measured_value", t.uint16_t, True),
        VOC_MIN_MEASURED_VALUE: ("min_measured_value", t.uint16_t, True),
        VOC_MAX_MEASURED_VALUE: ("max_measured_value", t.uint16_t, True),
        VOC_RESOLUTION: ("resolution", t.uint16_t, True),
    }
    server_commands = {}
    client_commands = {}

    def __init__(self, *args, **kwargs):
        """Init."""
        self._current_state = {}
        super().__init__(*args, **kwargs)
        self.endpoint.device.app_cluster = self

    def _update_attribute(self, attrid, value):
        super()._update_attribute(attrid, value)
        if attrid == VOC_MEASURED_VALUE and value is not None:
            self.endpoint.device.voc_bus.listener_event(VOC_REPORTED, value)
        if attrid == VOC_MIN_MEASURED_VALUE and value is not None:
            self.endpoint.device.voc_bus.listener_event(MIN_VOC_REPORTED, value)
        if attrid == VOC_MAX_MEASURED_VALUE and value is not None:
            self.endpoint.device.voc_bus.listener_event(MAX_VOC_REPORTED, value)
        if attrid == VOC_RESOLUTION and value is not None:
            self.endpoint.device.voc_bus.listener_event(VOC_RESOLUTION_REPORTED, value)
        _LOGGER.debug(
            "%s Develco VOC : [%s]",
            self.endpoint.device.ieee,
            self._attr_cache,
        )


class DevelcoRelativeHumidity(CustomCluster, RelativeHumidity):
    """Handles invalid values for Humidity."""

    def _update_attribute(self, attrid, value):
        # Drop values out of specified range (0-100% RH)
        if 0 <= value <= 10000:
            super()._update_attribute(attrid, value)
        _LOGGER.debug(
            "%s Develco Humidity : [%s]",
            self.endpoint.device.ieee,
            self._attr_cache,
        )


class DevelcoTemperatureMeasurement(CustomCluster, TemperatureMeasurement):
    """Handles invalid values for Temperature."""

    def _update_attribute(self, attrid, value):
        # Drop values out of specified range (0-50°C)
        if 0 <= value <= 5000:
            super()._update_attribute(attrid, value)
        _LOGGER.debug(
            "%s Develco Temperature : [%s]",
            self.endpoint.device.ieee,
            self._attr_cache,
        )


class EmulatedVOCMeasurement(LocalDataCluster):
    """VOC measurement cluster to receive reports from the Develco VOC cluster."""

    cluster_id = 0x042E
    name = "VOC Level"
    ep_attribute = "voc_level"
    attributes = {
        VOC_MEASURED_VALUE: ("measured_value", t.uint16_t, True),
        VOC_MIN_MEASURED_VALUE: ("min_measured_value", t.uint16_t, True),
        VOC_MAX_MEASURED_VALUE: ("max_measured_value", t.uint16_t, True),
        VOC_RESOLUTION: ("resolution", t.uint16_t, True),
    }
    MEASURED_VALUE_ID = 0x0000
    MIN_MEASURED_VALUE_ID = 0x0001
    MAX_MEASURED_VALUE_ID = 0x0002
    RESOLUTION_ID = 0x0003

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self.endpoint.device.voc_bus.add_listener(self)

    async def bind(self):
        """Bind cluster."""
        result = await self.endpoint.device.app_cluster.bind()
        return result

    async def write_attributes(self, attributes, manufacturer=None):
        """Ignore write_attributes."""
        return (0,)

    def _update_attribute(self, attrid, value):
        # Drop values out of specified range (0-60000 ppb)
        if 0 <= value <= 60000:
            # Convert ppb into mg/m³ approximation according to develco spec
            value = value * 0.0000045
            super()._update_attribute(attrid, value)

    def voc_reported(self, value):
        """VOC reported."""
        self._update_attribute(self.MEASURED_VALUE_ID, value)

    def min_voc_reported(self, value):
        """Minimum Measured VOC reported."""
        self._update_attribute(self.MIN_MEASURED_VALUE_ID, value)

    def max_voc_reported(self, value):
        """Maximum Measured VOC reported."""
        self._update_attribute(self.MAX_MEASURED_VALUE_ID, value)

    def voc_resolution_reported(self, value):
        """VOC Resolution reported."""
        self._update_attribute(self.RESOLUTION_ID, value)


class AQSZB110(CustomDevice):
    """Custom device Develco air quality sensor."""

    manufacturer_id_override = MANUFACTURER

    def __init__(self, *args, **kwargs):
        """Init."""
        self.voc_bus = Bus()
        super().__init__(*args, **kwargs)

    signature = {
        # <SimpleDescriptor endpoint=1 profile=49353 device_type=1 device_version=1
        # input_clusters=[3, 5, 6] output_clusters=[]>
        # <SimpleDescriptor endpoint=38 profile=260 device_type=770 device_version=0
        # input_clusters=[0, 1, 3, 32, 1026, 1029, 64515] output_clusters=[3, 10, 25]>
        MODELS_INFO: [
            (DEVELCO, "AQSZB-110"),
            ("frient A/S", "AQSZB-110"),
        ],
        ENDPOINTS: {
            1: {
                PROFILE_ID: 0xC0C9,
                DEVICE_TYPE: 1,
                INPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                ],
                OUTPUT_CLUSTERS: [],
            },
            38: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.TEMPERATURE_SENSOR,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    PollControl.cluster_id,
                    TemperatureMeasurement.cluster_id,
                    RelativeHumidity.cluster_id,
                    0xFC03,
                ],
                OUTPUT_CLUSTERS: [Identify.cluster_id, Time.cluster_id, Ota.cluster_id],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: 0xC0C9,
                DEVICE_TYPE: 1,
                INPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                ],
                OUTPUT_CLUSTERS: [],
            },
            38: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.TEMPERATURE_SENSOR,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    DevelcoPowerConfiguration,
                    Identify.cluster_id,
                    PollControl.cluster_id,
                    DevelcoTemperatureMeasurement,
                    DevelcoRelativeHumidity,
                    DevelcoVOCMeasurement,
                    EmulatedVOCMeasurement,
                ],
                OUTPUT_CLUSTERS: [Identify.cluster_id, Time.cluster_id, Ota.cluster_id],
            },
        },
    }
