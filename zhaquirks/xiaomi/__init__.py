"""Xiaomi common components for custom device handlers."""
import asyncio
import binascii
import logging

from zigpy import types as t
from zigpy.quirks import CustomCluster, CustomDevice
from zigpy.zcl.clusters.general import Basic, PowerConfiguration
from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement
from zigpy.zcl.clusters.measurement import (
    OccupancySensing,
    PressureMeasurement,
    RelativeHumidity,
    TemperatureMeasurement,
)
from zigpy.zcl.clusters.security import IasZone
import zigpy.zcl.foundation as foundation

from .. import Bus, LocalDataCluster
from ..const import (
    ATTRIBUTE_ID,
    ATTRIBUTE_NAME,
    CLUSTER_COMMAND,
    COMMAND_ATTRIBUTE_UPDATED,
    COMMAND_TRIPLE,
    MOTION_EVENT,
    OFF,
    ON,
    UNKNOWN,
    VALUE,
    ZHA_SEND_EVENT,
    ZONE_STATE,
)

BATTERY_LEVEL = "battery_level"
BATTERY_PERCENTAGE_REMAINING = 0x0021
BATTERY_REPORTED = "battery_reported"
BATTERY_SIZE = "battery_size"
BATTERY_VOLTAGE_MV = "battery_voltage_mV"
HUMIDITY_MEASUREMENT = "humidity_measurement"
HUMIDITY_REPORTED = "humidity_reported"
LUMI = "LUMI"
MODEL = 5
MOTION_TYPE = 0x000D
OCCUPANCY_STATE = 0
PATH = "path"
POWER = "power"
CONSUMPTION = "consumption"
VOLTAGE = "voltage"
PRESSURE_MEASUREMENT = "pressure_measurement"
PRESSURE_REPORTED = "pressure_reported"
STATE = "state"
TEMPERATURE = "temperature"
TEMPERATURE_MEASUREMENT = "temperature_measurement"
TEMPERATURE_REPORTED = "temperature_reported"
POWER_REPORTED = "power_reported"
CONSUMPTION_REPORTED = "consumption_reported"
VOLTAGE_REPORTED = "voltage_reported"
XIAOMI_AQARA_ATTRIBUTE = 0xFF01
XIAOMI_ATTR_3 = "X-attrib-3"
XIAOMI_ATTR_4 = "X-attrib-4"
XIAOMI_ATTR_5 = "X-attrib-5"
XIAOMI_ATTR_6 = "X-attrib-6"
XIAOMI_MIJA_ATTRIBUTE = 0xFF02
ZONE_TYPE = 0x0001

_LOGGER = logging.getLogger(__name__)


class XiaomiCustomDevice(CustomDevice):
    """Custom device representing xiaomi devices."""

    def __init__(self, *args, **kwargs):
        """Init."""
        self.battery_bus = Bus()
        if not hasattr(self, BATTERY_SIZE):
            self.battery_size = 10
        super().__init__(*args, **kwargs)


class BasicCluster(CustomCluster, Basic):
    """Xiaomi basic cluster implementation."""

    cluster_id = Basic.cluster_id

    def deserialize(self, data):
        """Deserialize cluster data."""
        try:
            return super().deserialize(data)
        except ValueError:
            hdr, data = foundation.ZCLHeader.deserialize(data)
            if not (
                hdr.frame_control.frame_type == foundation.FrameType.GLOBAL_COMMAND
                and hdr.command_id == 0x0A
            ):
                raise
            msg = "ValueError exception for: %s payload: %s"
            self.debug(msg, hdr, binascii.hexlify(data))
            newdata = b""
            while data:
                try:
                    attr, data = foundation.Attribute.deserialize(data)
                except ValueError:
                    attr_id, data = t.uint16_t.deserialize(data)
                    if attr_id not in (XIAOMI_AQARA_ATTRIBUTE, XIAOMI_MIJA_ATTRIBUTE):
                        raise
                    attr_type, data = t.uint8_t.deserialize(data)
                    val_len, data = t.uint8_t.deserialize(data)
                    val_len = t.uint8_t(val_len - 1)
                    val, data = data[:val_len], data[val_len:]
                    newdata += attr_id.serialize()
                    newdata += attr_type.serialize()
                    newdata += val_len.serialize() + val
                    continue
                newdata += attr.serialize()
            self.debug("new data: %s", binascii.hexlify(hdr.serialize() + newdata))
            return super().deserialize(hdr.serialize() + newdata)

    def _update_attribute(self, attrid, value):
        if attrid == XIAOMI_AQARA_ATTRIBUTE:
            attributes = self._parse_aqara_attributes(value.raw)
            super()._update_attribute(attrid, value.raw)
            if (
                MODEL in self._attr_cache
                and self._attr_cache[MODEL] == "lumi.sensor_switch.aq2"
            ):
                if value.raw == b"\x04!\xa8C\n!\x00\x00":
                    self.listener_event(ZHA_SEND_EVENT, self, COMMAND_TRIPLE, [])
        elif attrid == XIAOMI_MIJA_ATTRIBUTE:
            attributes = self._parse_mija_attributes(value)
        else:
            super()._update_attribute(attrid, value)
            if attrid == 0x0005:
                # 0x0005 = model attribute.
                # Xiaomi sensors send the model attribute when their reset button is
                # pressed quickly."""
                self.listener_event(
                    ZHA_SEND_EVENT,
                    self,
                    COMMAND_ATTRIBUTE_UPDATED,
                    {
                        ATTRIBUTE_ID: attrid,
                        ATTRIBUTE_NAME: self.attributes.get(attrid, [UNKNOWN])[0],
                        VALUE: value,
                    },
                )
            return

        _LOGGER.debug(
            "%s - Attribute report. attribute_id: [%s] value: [%s]",
            self.endpoint.device.ieee,
            attrid,
            attributes,
        )
        if BATTERY_LEVEL in attributes:
            self.endpoint.device.battery_bus.listener_event(
                BATTERY_REPORTED,
                attributes[BATTERY_LEVEL],
                attributes[BATTERY_VOLTAGE_MV],
            )
        if TEMPERATURE_MEASUREMENT in attributes:
            self.endpoint.device.temperature_bus.listener_event(
                TEMPERATURE_REPORTED, attributes[TEMPERATURE_MEASUREMENT]
            )
        if HUMIDITY_MEASUREMENT in attributes:
            self.endpoint.device.humidity_bus.listener_event(
                HUMIDITY_REPORTED, attributes[HUMIDITY_MEASUREMENT]
            )
        if PRESSURE_MEASUREMENT in attributes:
            self.endpoint.device.pressure_bus.listener_event(
                PRESSURE_REPORTED, attributes[PRESSURE_MEASUREMENT] / 100
            )
        if POWER in attributes:
            self.endpoint.device.power_bus.listener_event(
                POWER_REPORTED, attributes[POWER]
            )
        if CONSUMPTION in attributes:
            self.endpoint.device.consumption_bus.listener_event(
                CONSUMPTION_REPORTED, attributes[CONSUMPTION]
            )
        if VOLTAGE in attributes:
            self.endpoint.device.voltage_bus.listener_event(
                VOLTAGE_REPORTED, attributes[VOLTAGE] * 0.1
            )

    def _parse_aqara_attributes(self, value):
        """Parse non standard atrributes."""
        attributes = {}
        attribute_names = {
            1: BATTERY_VOLTAGE_MV,
            3: TEMPERATURE,
            4: XIAOMI_ATTR_4,
            5: XIAOMI_ATTR_5,
            6: XIAOMI_ATTR_6,
            10: PATH,
        }

        if MODEL in self._attr_cache and self._attr_cache[MODEL] in [
            "lumi.sensor_ht",
            "lumi.sens",
            "lumi.weather",
        ]:
            # Temperature sensors send temperature/humidity/pressure updates trough this
            # cluster instead of the respective clusters
            attribute_names.update(
                {
                    100: TEMPERATURE_MEASUREMENT,
                    101: HUMIDITY_MEASUREMENT,
                    102: PRESSURE_MEASUREMENT,
                }
            )
        elif MODEL in self._attr_cache and self._attr_cache[MODEL] in [
            "lumi.plug.maus01",
            "lumi.relay.c2acn01",
        ]:
            attribute_names.update({149: CONSUMPTION, 150: VOLTAGE, 152: POWER})

        result = {}
        while value:
            skey = int(value[0])
            svalue, value = foundation.TypeValue.deserialize(value[1:])
            result[skey] = svalue.value
        for item, val in result.items():
            key = (
                attribute_names[item]
                if item in attribute_names
                else "0xff01-" + str(item)
            )
            attributes[key] = val
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

    @staticmethod
    def _calculate_remaining_battery_percentage(voltage):
        """Calculate percentage."""
        # Min/Max values from https://github.com/louisZL/lumi-gateway-local-api
        min_voltage = 2800
        max_voltage = 3300
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
        self.endpoint.device.battery_bus.add_listener(self)
        if hasattr(self.endpoint.device, BATTERY_SIZE):
            self._update_attribute(
                self.BATTERY_SIZE_ATTR, self.endpoint.device.battery_size
            )
        else:
            self._update_attribute(self.BATTERY_SIZE_ATTR, 0xFF)
        self._update_attribute(self.BATTERY_QUANTITY_ATTR, 1)

    def battery_reported(self, voltage, raw_voltage):
        """Battery reported."""
        self._update_attribute(BATTERY_PERCENTAGE_REMAINING, voltage)
        self._update_attribute(self.BATTERY_VOLTAGE_ATTR, int(raw_voltage / 100))


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
            self.endpoint.device.motion_bus.listener_event(MOTION_EVENT)
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
        self.endpoint.device.motion_bus.add_listener(self)
        super()._update_attribute(ZONE_TYPE, MOTION_TYPE)

    def motion_event(self):
        """Motion event."""
        super().listener_event(CLUSTER_COMMAND, None, ZONE_STATE, [ON])

        _LOGGER.debug("%s - Received motion event message", self.endpoint.device.ieee)

        if self._timer_handle:
            self._timer_handle.cancel()

        loop = asyncio.get_event_loop()
        self._timer_handle = loop.call_later(120, self._turn_off)

    def _turn_off(self):
        _LOGGER.debug("%s - Resetting motion sensor", self.endpoint.device.ieee)
        self._timer_handle = None
        super().listener_event(CLUSTER_COMMAND, None, ZONE_STATE, [OFF])


class TemperatureMeasurementCluster(CustomCluster, TemperatureMeasurement):
    """Temperature cluster that filters out invalid temperature readings."""

    cluster_id = TemperatureMeasurement.cluster_id
    ATTR_ID = 0

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self.endpoint.device.temperature_bus.add_listener(self)

    def _update_attribute(self, attrid, value):
        # drop values above and below documented range for this sensor
        # value is in centi degrees
        if attrid == self.ATTR_ID and (-2000 <= value <= 6000):
            super()._update_attribute(attrid, value)

    def temperature_reported(self, value):
        """Temperature reported."""
        self._update_attribute(self.ATTR_ID, value)


class RelativeHumidityCluster(CustomCluster, RelativeHumidity):
    """Humidity cluster that filters out invalid humidity readings."""

    cluster_id = RelativeHumidity.cluster_id
    ATTR_ID = 0

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self.endpoint.device.humidity_bus.add_listener(self)

    def _update_attribute(self, attrid, value):
        # drop values above and below documented range for this sensor
        if attrid == self.ATTR_ID and (0 <= value <= 9999):
            super()._update_attribute(attrid, value)

    def humidity_reported(self, value):
        """Humidity reported."""
        self._update_attribute(self.ATTR_ID, value)


class PressureMeasurementCluster(CustomCluster, PressureMeasurement):
    """Pressure cluster to receive reports that are sent to the basic cluster."""

    cluster_id = PressureMeasurement.cluster_id
    ATTR_ID = 0

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self.endpoint.device.pressure_bus.add_listener(self)

    def pressure_reported(self, value):
        """Pressure reported."""
        self._update_attribute(self.ATTR_ID, value)


class ElectricalMeasurementCluster(CustomCluster, ElectricalMeasurement):
    """Electrical measurement cluster to receive reports that are sent to the basic cluster."""

    cluster_id = ElectricalMeasurement.cluster_id
    POWER_ID = 0x050B
    VOLTAGE_ID = 0x0500
    CONSUMPTION_ID = 0x0304

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self.endpoint.device.voltage_bus.add_listener(self)
        self.endpoint.device.consumption_bus.add_listener(self)
        self.endpoint.device.power_bus.add_listener(self)

    def power_reported(self, value):
        """Power reported."""
        self._update_attribute(self.POWER_ID, value)

    def voltage_reported(self, value):
        """Voltage reported."""
        self._update_attribute(self.VOLTAGE_ID, value)

    def consumption_reported(self, value):
        """Consumption reported."""
        self._update_attribute(self.CONSUMPTION_ID, value)

    async def read_attributes_raw(self, attributes, manufacturer=None):
        """Prevent remote reads."""
        attributes = [t.uint16_t(a) for a in attributes]
        values = [self._attr_cache.get(attr) for attr in attributes]
        return values
