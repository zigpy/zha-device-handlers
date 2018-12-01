import logging

from zigpy.zcl.clusters.general import Basic, PowerConfiguration
from zigpy.zcl.clusters.measurement import TemperatureMeasurement
from zigpy.quirks import CustomCluster, CustomDevice
from zhaquirks import LocalDataCluster, Bus
import zigpy.types as types

XIAOMI_ATTRIBUTE = 0xFF01
BATTERY_REPORTED = 'battery_reported'
TEMPERATURE_REPORTED = 'temperature_reported'
TEMPERATURE_MEASURED_VALUE = 0x0000
BATTERY_LEVEL = 'battery_level'
TEMPERATURE = 'temperature'
BATTERY_VOLTAGE_MV = 'battery_voltage_mV'
XIAOMI_ATTR_4 = 'X-attrib-4'
XIAOMI_ATTR_5 = 'X-attrib-5'
XIAOMI_ATTR_6 = 'X-attrib-6'
PATH = 'path'
BATTERY_PERCENTAGE_REMAINING = 0x0021

_LOGGER = logging.getLogger(__name__)


class XiaomiCustomDevice(CustomDevice):

    def __init__(self, *args, **kwargs):
        self.temperatureBus = Bus()
        self.batteryBus = Bus()
        super().__init__(*args, **kwargs)


class BasicCluster(CustomCluster, Basic):
    cluster_id = Basic.cluster_id

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _update_attribute(self, attrid, value):
        super()._update_attribute(attrid, value)
        if attrid == XIAOMI_ATTRIBUTE:
            attributes = self._parse_attributes(value)
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

    def _parse_attributes(self, value):
        """ parse non standard atrributes."""
        import zigpy.types as t
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

    def _calculate_remaining_battery_percentage(self, voltage):
        """calculate percentage."""
        min_voltage = 2500
        max_voltage = 3000
        percent = (voltage - min_voltage) / (max_voltage - min_voltage) * 100
        if percent > 100:
            percent = 100
        return percent


class PowerConfigurationCluster(LocalDataCluster, PowerConfiguration):
    cluster_id = PowerConfiguration.cluster_id
    BATTERY_VOLTAGE_ATTR = 0x0020
    BATTERY_SIZE_ATTR = 0x0031
    BATTERY_QUANTITY_ATTR = 0x0033

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.endpoint.device.batteryBus.add_listener(self)
        self._update_attribute(self.BATTERY_SIZE_ATTR, 0xff)
        self._update_attribute(self.BATTERY_QUANTITY_ATTR, 1)

    def battery_reported(self, voltage, rawVoltage):
        self._update_attribute(BATTERY_PERCENTAGE_REMAINING, voltage)
        self._update_attribute(BATTERY_VOLTAGE_MV, rawVoltage)


class TemperatureMeasurementCluster(LocalDataCluster, TemperatureMeasurement):
    cluster_id = TemperatureMeasurement.cluster_id

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.endpoint.device.temperatureBus.add_listener(self)

    def temperature_reported(self, rawTemperature):
        self._update_attribute(
            TEMPERATURE_MEASURED_VALUE,
            rawTemperature * 100
        )
