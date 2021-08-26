"""Xiaomi common components for custom device handlers."""
from __future__ import annotations

import logging
import math
from typing import Iterable, Iterator, Optional

from zigpy import types as t
import zigpy.device
from zigpy.profiles import zha
from zigpy.quirks import CustomCluster, CustomDevice
from zigpy.zcl.clusters.general import (
    AnalogInput,
    Basic,
    BinaryOutput,
    OnOff,
    PowerConfiguration,
)
from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement
from zigpy.zcl.clusters.measurement import (
    IlluminanceMeasurement,
    PressureMeasurement,
    RelativeHumidity,
    TemperatureMeasurement,
)
import zigpy.zcl.foundation as foundation
import zigpy.zdo
from zigpy.zdo.types import NodeDescriptor

from zhaquirks import (
    Bus,
    LocalDataCluster,
    MotionOnEvent,
    OccupancyWithReset,
    QuickInitDevice,
)
from zhaquirks.const import (
    ATTRIBUTE_ID,
    ATTRIBUTE_NAME,
    COMMAND_ATTRIBUTE_UPDATED,
    COMMAND_TRIPLE,
    UNKNOWN,
    VALUE,
    ZHA_SEND_EVENT,
)

BATTERY_LEVEL = "battery_level"
BATTERY_PERCENTAGE_REMAINING = 0x0021
BATTERY_REPORTED = "battery_reported"
BATTERY_SIZE = "battery_size"
BATTERY_SIZE_ATTR = 0x0031
BATTERY_QUANTITY_ATTR = 0x0033
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
ILLUMINANCE_MEASUREMENT = "illuminance_measurement"
ILLUMINANCE_REPORTED = "illuminance_reported"
XIAOMI_AQARA_ATTRIBUTE = 0xFF01
XIAOMI_ATTR_3 = "X-attrib-3"
XIAOMI_ATTR_4 = "X-attrib-4"
XIAOMI_ATTR_5 = "X-attrib-5"
XIAOMI_ATTR_6 = "X-attrib-6"
XIAOMI_MIJA_ATTRIBUTE = 0xFF02
XIAOMI_NODE_DESC = NodeDescriptor(
    byte1=2,
    byte2=64,
    mac_capability_flags=128,
    manufacturer_code=4151,
    maximum_buffer_size=127,
    maximum_incoming_transfer_size=100,
    server_mask=0,
    maximum_outgoing_transfer_size=100,
    descriptor_capability_field=0,
)
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


class XiaomiQuickInitDevice(XiaomiCustomDevice, QuickInitDevice):
    """Xiaomi devices eligible for QuickInit."""


class BasicCluster(CustomCluster, Basic):
    """Xiaomi basic cluster implementation."""

    cluster_id = Basic.cluster_id

    def _iter_parse_attr_report(
        self, data: bytes
    ) -> Iterator[foundation.Attribute, bytes]:
        """Yield all interpretations of the first attribute in an Xiaomi report."""

        # Peek at the attribute report
        attr_id, data = t.uint16_t.deserialize(data)
        attr_type, data = t.uint8_t.deserialize(data)

        if (
            attr_id not in (XIAOMI_AQARA_ATTRIBUTE, XIAOMI_MIJA_ATTRIBUTE)
            or attr_type != 0x42  # "Character String"
        ):
            # Assume other attributes are reported correctly
            data = attr_id.serialize() + attr_type.serialize() + data
            attribute, data = foundation.Attribute.deserialize(data)

            yield attribute, data
            return

        # Length of the "string" can be wrong
        val_len, data = t.uint8_t.deserialize(data)

        # Try every offset. Start with 0 to pass unbroken reports through.
        for offset in (0, -1, 1):
            fixed_len = val_len + offset

            if len(data) < fixed_len:
                continue

            val, final_data = data[:fixed_len], data[fixed_len:]
            attr_val = t.LVBytes(val)
            attr_type = 0x41  # The data type should be "Octet String"

            yield foundation.Attribute(
                attrid=attr_id,
                value=foundation.TypeValue(python_type=attr_type, value=attr_val),
            ), final_data

    def _interpret_attr_reports(
        self, data: bytes
    ) -> Iterable[tuple[foundation.Attribute]]:
        """Yield all valid interprations of a Xiaomi attribute report."""

        if not data:
            yield ()
            return

        try:
            parsed = list(self._iter_parse_attr_report(data))
        except (KeyError, ValueError):
            return

        for attr, remaining_data in parsed:
            for remaining_attrs in self._interpret_attr_reports(remaining_data):
                yield (attr,) + remaining_attrs

    def deserialize(self, data):
        """Deserialize cluster data."""
        hdr, data = foundation.ZCLHeader.deserialize(data)

        # Only handle attribute reports differently
        if (
            hdr.frame_control.frame_type != foundation.FrameType.GLOBAL_COMMAND
            or hdr.command_id != foundation.Command.Report_Attributes
        ):
            return super().deserialize(hdr.serialize() + data)

        reports = list(self._interpret_attr_reports(data))

        if not reports:
            _LOGGER.warning("Failed to parse Xiaomi attribute report: %r", data)
            return super().deserialize(hdr.serialize() + data)
        elif len(reports) > 1:
            _LOGGER.warning(
                "Xiaomi attribute report has multiple valid interpretations: %r",
                reports,
            )

        fixed_data = b"".join(attr.serialize() for attr in reports[0])

        return super().deserialize(hdr.serialize() + fixed_data)

    def _update_attribute(self, attrid, value):
        if attrid == XIAOMI_AQARA_ATTRIBUTE:
            attributes = self._parse_aqara_attributes(value)
            super()._update_attribute(attrid, value)
            if (
                MODEL in self._attr_cache
                and self._attr_cache[MODEL] == "lumi.sensor_switch.aq2"
            ):
                if value == b"\x04!\xa8C\n!\x00\x00":
                    self.listener_event(ZHA_SEND_EVENT, COMMAND_TRIPLE, [])
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
        if BATTERY_VOLTAGE_MV in attributes:
            self.endpoint.device.battery_bus.listener_event(
                BATTERY_REPORTED, attributes[BATTERY_VOLTAGE_MV]
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
        if ILLUMINANCE_MEASUREMENT in attributes:
            self.endpoint.device.illuminance_bus.listener_event(
                ILLUMINANCE_REPORTED, attributes[ILLUMINANCE_MEASUREMENT]
            )

    def _parse_aqara_attributes(self, value):
        """Parse non standard attributes."""
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
        elif (
            MODEL in self._attr_cache
            and self._attr_cache[MODEL] == "lumi.sensor_motion.aq2"
        ):
            attribute_names.update({11: ILLUMINANCE_MEASUREMENT})

        result = {}

        # Some attribute reports end with a stray null byte
        while value not in (b"", b"\x00"):
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

        return attributes

    def _parse_mija_attributes(self, value):
        """Parse non standard attributes."""
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

        return attributes


class BinaryOutputInterlock(CustomCluster, BinaryOutput):
    """Xiaomi binaryoutput cluster with added interlock attribute."""

    manufacturer_attributes = {0xFF06: ("interlock", t.Bool)}


class XiaomiPowerConfiguration(PowerConfiguration, LocalDataCluster):
    """Xiaomi power configuration cluster implementation."""

    BATTERY_VOLTAGE_ATTR = 0x0020
    BATTERY_PERCENTAGE_REMAINING = 0x0021
    MAX_VOLTS_MV = 3100
    MIN_VOLTS_MV = 2820

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self.endpoint.device.battery_bus.add_listener(self)
        self._CONSTANT_ATTRIBUTES = {
            BATTERY_QUANTITY_ATTR: 1,
            BATTERY_SIZE_ATTR: getattr(self.endpoint.device, BATTERY_SIZE, 0xFF),
        }
        self._slope = 200 / (self.MAX_VOLTS_MV - self.MIN_VOLTS_MV)

    def battery_reported(self, voltage_mv: int) -> None:
        """Battery reported."""
        self._update_attribute(self.BATTERY_VOLTAGE_ATTR, round(voltage_mv / 100, 1))
        self._update_battery_percentage(voltage_mv)

    def _update_battery_percentage(self, voltage_mv: int) -> None:
        voltage_mv = max(voltage_mv, self.MIN_VOLTS_MV)
        voltage_mv = min(voltage_mv, self.MAX_VOLTS_MV)

        percent = round((voltage_mv - self.MIN_VOLTS_MV) * self._slope)

        self.debug(
            "Voltage mV: [Min]:%s < [RAW]:%s < [Max]:%s, Battery Percent: %s",
            self.MIN_VOLTS_MV,
            voltage_mv,
            self.MAX_VOLTS_MV,
            percent / 2,
        )

        self._update_attribute(self.BATTERY_PERCENTAGE_REMAINING, percent)


class OccupancyCluster(OccupancyWithReset):
    """Occupancy cluster."""


class MotionCluster(LocalDataCluster, MotionOnEvent):
    """Motion cluster."""

    _CONSTANT_ATTRIBUTES = {ZONE_TYPE: MOTION_TYPE}
    reset_s: int = 70


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

    def _update_attribute(self, attrid, value):
        # drop unreasonable values
        # value is in hectopascals
        if attrid == self.ATTR_ID and (0 <= value <= 1100):
            super()._update_attribute(attrid, value)

    def pressure_reported(self, value):
        """Pressure reported."""
        self._update_attribute(self.ATTR_ID, value)


class AnalogInputCluster(CustomCluster, AnalogInput):
    """Analog input cluster, only used to relay power consumption information to ElectricalMeasurementCluster."""

    cluster_id = AnalogInput.cluster_id

    def __init__(self, *args, **kwargs):
        """Init."""
        self._current_state = {}
        super().__init__(*args, **kwargs)

    def _update_attribute(self, attrid, value):
        super()._update_attribute(attrid, value)
        if value is not None and value >= 0:
            self.endpoint.device.power_bus.listener_event(POWER_REPORTED, value)


class ElectricalMeasurementCluster(LocalDataCluster, ElectricalMeasurement):
    """Electrical measurement cluster to receive reports that are sent to the basic cluster."""

    cluster_id = ElectricalMeasurement.cluster_id
    POWER_ID = 0x050B
    VOLTAGE_ID = 0x0500
    CONSUMPTION_ID = 0x0304
    _CONSTANT_ATTRIBUTES = {
        0x0402: 1,  # power_multiplier
        0x0403: 1,  # power_divisor
        0x0604: 1,  # ac_power_multiplier
        0x0605: 1,  # ac_power_divisor
    }

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


class IlluminanceMeasurementCluster(CustomCluster, IlluminanceMeasurement):
    """Multistate input cluster."""

    cluster_id = IlluminanceMeasurement.cluster_id
    ATTR_ID = 0

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self.endpoint.device.illuminance_bus.add_listener(self)

    def _update_attribute(self, attrid, value):
        if attrid == self.ATTR_ID and value > 0:
            value = 10000 * math.log10(value) + 1
        super()._update_attribute(attrid, value)

    def illuminance_reported(self, value):
        """Illuminance reported."""
        self._update_attribute(self.ATTR_ID, value)


class OnOffCluster(OnOff, CustomCluster):
    """Aqara wall switch cluster."""

    def command(
        self,
        command_id: foundation.Command | int | t.uint8_t,
        *args,
        manufacturer: Optional[int | t.uint16_t] = None,
        expect_reply: bool = True,
        tsn: Optional[int | t.uint8_t] = None
    ):
        """Command handler."""
        src_ep = 1
        dst_ep = self.endpoint.endpoint_id
        device = self.endpoint.device
        if tsn is None:
            tsn = self._endpoint.device.application.get_sequence()
        return device.request(
            # device,
            zha.PROFILE_ID,
            OnOff.cluster_id,
            src_ep,
            dst_ep,
            tsn,
            bytes([src_ep, tsn, command_id]),
            expect_reply=expect_reply,
        )


def handle_quick_init(
    sender: zigpy.device.Device,
    profile: int,
    cluster: int,
    src_ep: int,
    dst_ep: int,
    message: bytes,
) -> Optional[bool]:
    """Handle message from an uninitialized device which could be a xiaomi."""
    if src_ep == 0:
        return

    hdr, data = foundation.ZCLHeader.deserialize(message)
    sender.debug(
        """Received ZCL while uninitialized on endpoint id %s, cluster 0x%04x """
        """id, hdr: %s, payload: %s""",
        src_ep,
        cluster,
        hdr,
        data,
    )
    if hdr.frame_control.is_cluster:
        return

    try:
        schema = foundation.COMMANDS[hdr.command_id][0]
        args, data = t.deserialize(data, schema)
    except (KeyError, ValueError):
        sender.debug("Failed to deserialize ZCL global command")
        return

    sender.debug("Uninitialized device command '%s' args: %s", hdr.command_id, args)
    if hdr.command_id != foundation.Command.Report_Attributes or cluster != 0:
        return

    for attr_rec in args[0]:
        if attr_rec.attrid == 5:
            break
    else:
        return

    model = attr_rec.value.value
    if not model:
        return

    for quirk in zigpy.quirks.get_quirk_list(LUMI, model):
        if issubclass(quirk, XiaomiQuickInitDevice):
            sender.debug("Found '%s' quirk for '%s' model", quirk.__name__, model)
            try:
                sender = quirk.from_signature(sender, model)
            except (AssertionError, KeyError) as ex:
                _LOGGER.debug(
                    "Found quirk for quick init, but failed to init: %s", str(ex)
                )
                continue
            break
    else:
        return

    sender.cancel_initialization()
    sender.application.device_initialized(sender)
    sender.info(
        "Was quickly initialized from '%s.%s' quirk", quirk.__module__, quirk.__name__
    )
    return True


zigpy.quirks.register_uninitialized_device_message_handler(handle_quick_init)
