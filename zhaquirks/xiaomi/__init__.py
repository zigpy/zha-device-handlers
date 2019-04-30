"""Xiaomi common components for custom device handlers."""
import asyncio
import logging

from zigpy.zcl.clusters.general import Basic, PowerConfiguration
from zigpy.zcl.clusters.measurement import (
    TemperatureMeasurement, OccupancySensing
)
from zigpy.zcl.clusters.security import IasZone
from zigpy.quirks import CustomCluster, CustomDevice
from zhaquirks import LocalDataCluster, Bus

XIAOMI_AQARA_ATTRIBUTE = 0xFF01
XIAOMI_MIJA_ATTRIBUTE = 0xFF02
BATTERY_REPORTED = 'battery_reported'
TEMPERATURE_REPORTED = 'temperature_reported'
TEMPERATURE_MEASURED_VALUE = 0x0000
BATTERY_LEVEL = 'battery_level'
TEMPERATURE = 'temperature'
BATTERY_VOLTAGE_MV = 'battery_voltage_mV'
XIAOMI_ATTR_3 = 'X-attrib-3'
XIAOMI_ATTR_4 = 'X-attrib-4'
XIAOMI_ATTR_5 = 'X-attrib-5'
XIAOMI_ATTR_6 = 'X-attrib-6'
STATE = 'state'
PATH = 'path'
BATTERY_PERCENTAGE_REMAINING = 0x0021
OCCUPANCY_STATE = 0
ZONE_STATE = 0
ON = 1
OFF = 0
ZONE_TYPE = 0x0001
MOTION_TYPE = 0x000d

_LOGGER = logging.getLogger(__name__)


class XiaomiCustomDevice(CustomDevice):
    """Custom device representing xiaomi devices."""

    def __init__(self, *args, **kwargs):
        """Init."""
        self.temperatureBus = Bus()
        self.batteryBus = Bus()
        if not hasattr(self, 'battery_size'):
            self.battery_size = 10
        super().__init__(*args, **kwargs)


class BasicCluster(CustomCluster, Basic):
    """Xiaomi basic cluster implementation."""

    cluster_id = Basic.cluster_id

    def _update_attribute(self, attrid, value):
        if attrid != XIAOMI_MIJA_ATTRIBUTE:
            super()._update_attribute(attrid, value)

        attributes = {}
        if attrid == XIAOMI_AQARA_ATTRIBUTE:
            attributes = self._parse_aqara_attributes(value)
        elif attrid == XIAOMI_MIJA_ATTRIBUTE:
            attributes = self._parse_mija_attributes(value)

        _LOGGER.debug(
            "%s - Attribute report. attribute_id: [%s] value: [%s]",
            self.endpoint.device._ieee,
            attrid,
            attributes
        )
        if BATTERY_LEVEL in attributes:
            self.endpoint.device.batteryBus.listener_event(
                BATTERY_REPORTED,
                attributes[BATTERY_LEVEL],
                attributes[BATTERY_VOLTAGE_MV]
            )
        if TEMPERATURE in attributes:
            self.endpoint.device.temperatureBus.listener_event(
                TEMPERATURE_REPORTED,
                attributes[TEMPERATURE]
            )

    def _parse_aqara_attributes(self, value):
        """Parse non standard atrributes."""
        from zigpy.zcl import foundation as f
        attributes = {}
        attribute_names = {
            1: BATTERY_VOLTAGE_MV,
            3: TEMPERATURE,
            4: XIAOMI_ATTR_4,
            5: XIAOMI_ATTR_5,
            6: XIAOMI_ATTR_6,
            10: PATH
        }
        result = {}
        while value:
            skey = int(value[0])
            svalue, value = f.TypeValue.deserialize(value[1:])
            result[skey] = svalue.value
        for item, value in result.items():
            key = attribute_names[item] \
                if item in attribute_names else "0xff01-" + str(item)
            attributes[key] = value
        if BATTERY_VOLTAGE_MV in attributes:
            attributes[BATTERY_LEVEL] = int(
                self._calculate_remaining_battery_percentage(
                    attributes[BATTERY_VOLTAGE_MV]
                )
            )
        return attributes

    def _parse_mija_attributes(self, value):
        """Parse non standard atrributes."""
        attributes = {}
        attribute_names = (
            STATE,
            BATTERY_VOLTAGE_MV,
            XIAOMI_ATTR_3,
            XIAOMI_ATTR_4,
            XIAOMI_ATTR_5,
            XIAOMI_ATTR_6,
        )
        result = []

        for attr_value in value:
            result.append(attr_value.value)
        attributes = dict(zip(attribute_names, result))

        if BATTERY_VOLTAGE_MV in attributes:
            attributes[BATTERY_LEVEL] = int(
                self._calculate_remaining_battery_percentage(
                    attributes[BATTERY_VOLTAGE_MV]
                )
            )

        return attributes

    def _calculate_remaining_battery_percentage(self, voltage):
        """Calculate percentage."""
        min_voltage = 2500
        max_voltage = 3000
        percent = (voltage - min_voltage) / (max_voltage - min_voltage) * 200
        return min(200, percent)


class PowerConfigurationCluster(LocalDataCluster, PowerConfiguration):
    """Xiaomi power configuration cluster implementation."""

    cluster_id = PowerConfiguration.cluster_id
    BATTERY_VOLTAGE_ATTR = 0x0020
    BATTERY_SIZE_ATTR = 0x0031
    BATTERY_QUANTITY_ATTR = 0x0033

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self.endpoint.device.batteryBus.add_listener(self)
        if hasattr(self.endpoint.device, 'battery_size'):
            self._update_attribute(
                self.BATTERY_SIZE_ATTR,
                self.endpoint.device.battery_size
            )
        else:
            self._update_attribute(self.BATTERY_SIZE_ATTR, 0xff)
        self._update_attribute(self.BATTERY_QUANTITY_ATTR, 1)

    def battery_reported(self, voltage, rawVoltage):
        """Battery reported."""
        self._update_attribute(BATTERY_PERCENTAGE_REMAINING, voltage)
        self._update_attribute(self.BATTERY_VOLTAGE_ATTR,
                               int(rawVoltage / 100))


class TemperatureMeasurementCluster(LocalDataCluster, TemperatureMeasurement):
    """Xiaomi temperature measurement cluster implementation."""

    cluster_id = TemperatureMeasurement.cluster_id

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self.endpoint.device.temperatureBus.add_listener(self)

    def temperature_reported(self, rawTemperature):
        """Temperature reported."""
        self._update_attribute(
            TEMPERATURE_MEASURED_VALUE,
            rawTemperature * 100
        )


class OccupancyCluster(CustomCluster, OccupancySensing):
    """Occupancy cluster."""

    cluster_id = OccupancySensing.cluster_id

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self._timer_handle = None

    def _update_attribute(self, attrid, value):
        super()._update_attribute(attrid, value)

        if attrid == OCCUPANCY_STATE and value == ON:
            if self._timer_handle:
                self._timer_handle.cancel()
            self.endpoint.device.motionBus.listener_event('motion_event')
            loop = asyncio.get_event_loop()
            self._timer_handle = loop.call_later(600, self._turn_off)

    def _turn_off(self):
        self._timer_handle = None
        self._update_attribute(OCCUPANCY_STATE, OFF)


class MotionCluster(LocalDataCluster, IasZone):
    """Motion cluster."""

    cluster_id = IasZone.cluster_id

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self._timer_handle = None
        self.endpoint.device.motionBus.add_listener(self)
        super()._update_attribute(ZONE_TYPE, MOTION_TYPE)

    def motion_event(self):
        """Motion event."""
        super().listener_event(
            'cluster_command',
            None,
            ZONE_STATE,
            [ON]
        )

        _LOGGER.debug(
            "%s - Received motion event message",
            self.endpoint.device._ieee
        )

        if self._timer_handle:
            self._timer_handle.cancel()

        loop = asyncio.get_event_loop()
        self._timer_handle = loop.call_later(120, self._turn_off)

    def _turn_off(self):
        _LOGGER.debug(
            "%s - Resetting motion sensor",
            self.endpoint.device._ieee
        )
        self._timer_handle = None
        super().listener_event(
            'cluster_command',
            None,
            ZONE_STATE,
            [OFF]
        )
