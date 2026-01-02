"""Aqara E1 Radiator Thermostat Quirk."""

from __future__ import annotations

from functools import reduce
import logging
import math
import struct
from typing import Any, Final

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
from zigpy.quirks.v2.homeassistant import EntityType, UnitOfTemperature
from zigpy.quirks.v2.homeassistant.binary_sensor import BinarySensorDeviceClass
from zigpy.quirks.v2.homeassistant.number import NumberDeviceClass
import zigpy.types as t
from zigpy.zcl.clusters.general import Basic, DeviceTemperature
from zigpy.zcl.clusters.hvac import Thermostat
from zigpy.zcl.foundation import ZCLAttributeDef

from zhaquirks import LocalDataCluster
from zhaquirks.xiaomi import LUMI, XiaomiAqaraE1Cluster, XiaomiPowerConfiguration

_LOGGER = logging.getLogger(__name__)

ZCL_SYSTEM_MODE = Thermostat.attributes_by_name["system_mode"].id

XIAOMI_SYSTEM_MODE_MAP = {
    0: Thermostat.SystemMode.Off,
    1: Thermostat.SystemMode.Heat,
}


class SystemMode(t.enum8):
    """Xiaomi TRV system mode.

    Maps to ZCL Thermostat.SystemMode but with Xiaomi-specific values.
    """

    Off = 0x00  # Heating disabled
    Heat = 0x01  # Heating enabled


SYSTEM_MODE = 0x0271
PRESET = 0x0272
WINDOW_DETECTION = 0x0273
VALVE_DETECTION = 0x0274
VALVE_ALARM = 0x0275
CALIBRATE = 0x0270
CHILD_LOCK = 0x0277
AWAY_PRESET_TEMPERATURE = 0x0279
WINDOW_OPEN = 0x027A
CALIBRATED = 0x027B
SCHEDULE = 0x027D
SCHEDULE_SETTINGS = 0x0276
SENSOR = 0x027E
BATTERY_PERCENTAGE = 0x040A
HEARTBEAT = 0x00F7

XIAOMI_MANUFACTURER_CODE = 0x115F

# Heartbeat data keys (from TLV structure)
HEARTBEAT_DEVICE_TEMPERATURE = 3
HEARTBEAT_POWER_OUTAGE_COUNT = 5
HEARTBEAT_FIRMWARE_VERSION = 13
HEARTBEAT_PRESET = 101
HEARTBEAT_LOCAL_TEMPERATURE = 102
HEARTBEAT_HEATING_SETPOINT = 103
HEARTBEAT_VALVE_ALARM = 104
HEARTBEAT_BATTERY = 105


class Preset(t.enum8):
    """TRV operating preset.

    Determines the operating mode of the thermostat.
    """

    Manual = 0x00  # Manual temperature control
    Auto = 0x01  # Automatic schedule-based control
    Away = 0x02  # Away/vacation mode with reduced temperature
    Setup = 0x03  # Initial setup mode after powering ("E11" on display)


class SensorMode(t.enum8):
    """Temperature sensor mode.

    Determines which temperature source the TRV uses for regulation.
    """

    Internal = 0x00  # Use internal temperature sensor (at the radiator)
    ExternalPaired = 0x01  # External Aqara sensor paired via Aqara Hub (automatic)
    ExternalInput = 0x02  # External temperature input via automation (manual updates)


DAYS_MAP = {
    "mon": 0x02,
    "tue": 0x04,
    "wed": 0x08,
    "thu": 0x10,
    "fri": 0x20,
    "sat": 0x40,
    "sun": 0x80,
}
NEXT_DAY_FLAG = 1 << 15


class ThermostatCluster(CustomCluster, Thermostat):
    """Thermostat cluster."""

    # remove cooling mode
    _CONSTANT_ATTRIBUTES = {
        Thermostat.attributes_by_name[
            "ctrl_sequence_of_oper"
        ].id: Thermostat.ControlSequenceOfOperation.Heating_Only
    }

    async def read_attributes(
        self,
        attributes: list[int | str],
        allow_cache: bool = False,
        only_cache: bool = False,
        manufacturer: int | t.uint16_t | None = None,
    ):
        """Pass reading attributes to Xiaomi cluster if applicable."""
        successful_r, failed_r = {}, {}
        remaining_attributes = attributes.copy()

        # read system_mode from Xiaomi cluster (can be numeric or string)
        if ZCL_SYSTEM_MODE in attributes or "system_mode" in attributes:
            self.debug("Passing 'system_mode' read to Xiaomi cluster")

            if ZCL_SYSTEM_MODE in attributes:
                remaining_attributes.remove(ZCL_SYSTEM_MODE)
            if "system_mode" in attributes:
                remaining_attributes.remove("system_mode")

            successful_r, failed_r = await self.endpoint.opple_cluster.read_attributes(
                [SYSTEM_MODE], allow_cache, only_cache, manufacturer
            )
            # convert Xiaomi system_mode to ZCL attribute
            if SYSTEM_MODE in successful_r:
                successful_r[ZCL_SYSTEM_MODE] = XIAOMI_SYSTEM_MODE_MAP[
                    successful_r.pop(SYSTEM_MODE)
                ]
        # read remaining attributes from thermostat cluster
        if remaining_attributes:
            remaining_result = await super().read_attributes(
                remaining_attributes, allow_cache, only_cache, manufacturer
            )
            successful_r.update(remaining_result[0])
            failed_r.update(remaining_result[1])
        return successful_r, failed_r

    async def write_attributes(
        self, attributes: dict[str | int, Any], manufacturer: int | None = None
    ) -> list:
        """Pass writing attributes to Xiaomi cluster if applicable."""
        result = []
        remaining_attributes = attributes.copy()
        system_mode_value = None

        # check if system_mode is being written (can be numeric or string)
        if ZCL_SYSTEM_MODE in attributes:
            remaining_attributes.pop(ZCL_SYSTEM_MODE)
            system_mode_value = attributes.get(ZCL_SYSTEM_MODE)
        if "system_mode" in attributes:
            remaining_attributes.pop("system_mode")
            system_mode_value = attributes.get("system_mode")

        # write system_mode to Xiaomi cluster if applicable
        if system_mode_value is not None:
            self.debug("Passing 'system_mode' write to Xiaomi cluster")
            result += await self.endpoint.opple_cluster.write_attributes(
                {SYSTEM_MODE: min(int(system_mode_value), 1)}
            )

        # write remaining attributes to thermostat cluster
        if remaining_attributes:
            result += await super().write_attributes(remaining_attributes, manufacturer)
        return result


class ScheduleEvent:
    """Schedule event object."""

    _is_next_day = False

    def __init__(self, value, is_next_day=False):
        """Create ScheduleEvent object from bytes or string."""
        if isinstance(value, bytes):
            self._verify_buffer_len(value)
            self._time = self._read_time_from_buf(value)
            self._temp = self._read_temp_from_buf(value)
            self._validate_time(self._time)
            self._validate_temp(self._temp)
        elif isinstance(value, str):
            groups = value.split(",")
            if len(groups) != 2:
                raise ValueError("Time and temperature must contain ',' separator")
            self._time = self._parse_time(groups[0])
            self._temp = self._parse_temp(groups[1])
            self._validate_time(self._time)
            self._validate_temp(self._temp)
        else:
            raise TypeError(
                f"Cannot create ScheduleEvent object from type: {type(value)}"
            )
        self._is_next_day = is_next_day

    @staticmethod
    def _verify_buffer_len(buf):
        if len(buf) != 6:
            raise ValueError("Buffer size must equal 6")

    @staticmethod
    def _read_time_from_buf(buf):
        time = struct.unpack_from(">H", buf, offset=0)[0]
        time &= ~NEXT_DAY_FLAG
        return time

    @staticmethod
    def _parse_time(string):
        parts = string.split(":")
        if len(parts) != 2:
            raise ValueError("Time must contain ':' separator")

        hours = int(parts[0])
        minutes = int(parts[1])

        return hours * 60 + minutes

    @staticmethod
    def _read_temp_from_buf(buf):
        return struct.unpack_from(">H", buf, offset=4)[0] / 100

    @staticmethod
    def _parse_temp(string):
        return float(string)

    @staticmethod
    def _validate_time(time):
        if time <= 0:
            raise ValueError("Time must be between 00:00 and 23:59")
        if time > 24 * 60:
            raise ValueError("Time must be between 00:00 and 23:59")

    @staticmethod
    def _validate_temp(temp):
        if temp < 5:
            raise ValueError("Temperature must be between 5 and 30 °C")
        if temp > 30:
            raise ValueError("Temperature must be between 5 and 30 °C")
        if (temp * 10) % 5 != 0:
            raise ValueError("Temperature must be whole or half degrees")

    def _write_time_to_buf(self, buf):
        time = self._time
        if self._is_next_day:
            time |= NEXT_DAY_FLAG
        struct.pack_into(">H", buf, 0, time)

    def _write_temp_to_buf(self, buf):
        struct.pack_into(">H", buf, 4, int(self._temp * 100))

    def is_next_day(self):
        """Return if event is on the next day."""
        return self._is_next_day

    def set_next_day(self, is_next_day):
        """Set if event is on the next day."""
        self._is_next_day = is_next_day

    def get_time(self):
        """Return event time."""
        return self._time

    def __str__(self):
        """Return event as string."""
        return f"{math.floor(self._time / 60)}:{f'{self._time % 60:0>2}'},{f'{self._temp:.1f}'}"

    def serialize(self):
        """Serialize event to bytes."""
        result = bytearray(6)
        self._write_time_to_buf(result)
        self._write_temp_to_buf(result)
        return result


class ScheduleSettings(t.LVBytes):
    """Schedule settings object."""

    def __new__(cls, value):
        """Create ScheduleSettings object from bytes or string."""
        day_selection = None
        events = [None] * 4
        if isinstance(value, bytes):
            ScheduleSettings._verify_buffer_len(value)
            ScheduleSettings._verify_magic_byte(value)
            day_selection = ScheduleSettings._read_day_selection(value)
            for i in range(4):
                events[i] = ScheduleSettings._read_event(value, i)
        elif isinstance(value, str):
            groups = value.split("|")
            ScheduleSettings._verify_string(groups)
            day_selection = ScheduleSettings._read_day_selection(groups[0])
            for i in range(4):
                events[i] = ScheduleSettings._read_event(groups[i + 1], i)
        else:
            raise TypeError(
                f"Cannot create ScheduleSettings object from type: {type(value)}"
            )

        for i in range(1, 4):
            if events[i].get_time() < events[i - 1].get_time():
                events[i].set_next_day(True)
        ScheduleSettings._verify_event_durations(events)

        result = bytearray(b"\x04")
        result.append(ScheduleSettings._get_day_selection_byte(day_selection))
        for e in events:
            result.extend(e.serialize())
        return super().__new__(cls, bytes(result))

    @staticmethod
    def _verify_buffer_len(buf):
        if len(buf) != 26:
            raise ValueError("Buffer size must equal 26")

    @staticmethod
    def _verify_magic_byte(buf):
        if struct.unpack_from("c", buf, offset=0)[0][0] != 0x04:
            raise ValueError("Magic byte must be equal to 0x04")

    @staticmethod
    def _verify_string(groups):
        if len(groups) != 5:
            raise ValueError("There must be 5 groups in a string")
        days = groups[0].split(",")
        ScheduleSettings._verify_day_selection_in_str(days)

    @staticmethod
    def _verify_day_selection_in_str(days):
        if len(days) == 0 or len(days) > 7:
            raise ValueError("Number of days selected must be between 1 and 7")
        if len(days) != len(set(days)):
            raise ValueError("Duplicate day names present")
        for d in days:
            if d not in DAYS_MAP:
                raise ValueError(
                    f"String: {d} is not a valid day name, valid names: mon, tue, wed, thu, fri, sat, sun"
                )

    @staticmethod
    def _read_day_selection(value):
        day_selection = []
        if isinstance(value, bytes):
            byte = struct.unpack_from("c", value, offset=1)[0][0]
            if byte & 0x01:
                raise ValueError("Incorrect day selected")
            for i, v in DAYS_MAP.items():
                if byte & v:
                    day_selection.append(i)
            ScheduleSettings._verify_day_selection_in_str(day_selection)
        elif isinstance(value, str):
            day_selection = value.split(",")
            ScheduleSettings._verify_day_selection_in_str(day_selection)
        return day_selection

    @staticmethod
    def _read_event(value, index):
        if isinstance(value, bytes):
            event_buf = value[2 + index * 6 : 8 + index * 6]
            return ScheduleEvent(event_buf)
        elif isinstance(value, str):
            return ScheduleEvent(value)

    @staticmethod
    def _verify_event_durations(events):
        full_day = 24 * 60
        prev_time = events[0].get_time()
        durations = []
        for i in range(1, 4):
            event = events[i]
            if event.is_next_day():
                durations.append(full_day - prev_time + event.get_time())
            else:
                durations.append(event.get_time() - prev_time)
            prev_time = event.get_time()
        if any(d < 60 for d in durations):
            raise ValueError("The individual times must be at least 1 hour apart")
        if reduce((lambda x, y: x + y), durations) > full_day:
            raise ValueError("The start and end times must be at most 24 hours apart")

    @staticmethod
    def _get_day_selection_byte(day_selection):
        byte = 0x00
        for d in day_selection:
            byte |= DAYS_MAP[d]
        return byte

    def __str__(self):
        """Return ScheduleSettings as string."""
        day_selection = ScheduleSettings._read_day_selection(self)
        events = [None] * 4
        for i in range(4):
            events[i] = ScheduleSettings._read_event(self, i)
        result = ",".join(day_selection)
        for e in events:
            result += f"|{e}"
        return result


class LocalDeviceTemperatureCluster(LocalDataCluster, DeviceTemperature):
    """Device temperature cluster for internal TRV temperature."""

    _CONSTANT_ATTRIBUTES = {
        DeviceTemperature.AttributeDefs.min_temp_experienced.id: -4000,
        DeviceTemperature.AttributeDefs.max_temp_experienced.id: 12500,
    }


# ZCL data type sizes for heartbeat parsing (type_id: (size, signed))
_ZCL_TYPE_SIZES: dict[int, tuple[int, bool]] = {
    0x10: (1, False),  # Bool
    0x20: (1, False),  # uint8
    0x21: (2, False),  # uint16
    0x22: (3, False),  # uint24
    0x23: (4, False),  # uint32
    0x24: (5, False),  # uint40
    0x25: (6, False),  # uint48
    0x28: (1, True),  # int8
    0x29: (2, True),  # int16
    0x2B: (4, True),  # int32
}


def _parse_heartbeat(value: bytes) -> dict[int, Any]:
    """Parse Xiaomi TLV heartbeat structure.

    The heartbeat is a TLV-encoded structure where each entry consists of:
    - 1 byte: key/index
    - 1 byte: data type (ZCL type)
    - N bytes: value (length depends on type)

    Returns a dictionary mapping keys to their parsed values.
    """
    result: dict[int, Any] = {}
    if not value or not isinstance(value, (bytes, bytearray)):
        return result

    i = 0
    while i < len(value) - 1:
        key = value[i]
        data_type = value[i + 1]

        try:
            if data_type in _ZCL_TYPE_SIZES:
                size, signed = _ZCL_TYPE_SIZES[data_type]
                result[key] = int.from_bytes(
                    value[i + 2 : i + 2 + size], "little", signed=signed
                )
                i += 2 + size
            elif data_type == 0x39:  # float (single precision)
                result[key] = struct.unpack("<f", value[i + 2 : i + 6])[0]
                i += 6
            else:
                _LOGGER.debug(
                    "Unknown data type 0x%02x at position %d in heartbeat",
                    data_type,
                    i,
                )
                break
        except (IndexError, struct.error):
            _LOGGER.debug("Error parsing heartbeat at position %d", i)
            break

    return result


class AqaraThermostatSpecificCluster(XiaomiAqaraE1Cluster):
    """Aqara manufacturer specific settings."""

    class AttributeDefs(XiaomiAqaraE1Cluster.AttributeDefs):
        """Attribute definitions."""

        heartbeat: Final = ZCLAttributeDef(
            id=HEARTBEAT, type=t.LVBytes, is_manufacturer_specific=True
        )
        calibrate: Final = ZCLAttributeDef(
            id=CALIBRATE, type=t.uint8_t, is_manufacturer_specific=True
        )
        system_mode: Final = ZCLAttributeDef(
            id=SYSTEM_MODE, type=t.uint8_t, is_manufacturer_specific=True
        )
        preset: Final = ZCLAttributeDef(
            id=PRESET, type=t.uint8_t, is_manufacturer_specific=True
        )
        window_detection: Final = ZCLAttributeDef(
            id=WINDOW_DETECTION, type=t.uint8_t, is_manufacturer_specific=True
        )
        valve_detection: Final = ZCLAttributeDef(
            id=VALVE_DETECTION, type=t.uint8_t, is_manufacturer_specific=True
        )
        valve_alarm: Final = ZCLAttributeDef(
            id=VALVE_ALARM, type=t.uint8_t, is_manufacturer_specific=True
        )
        child_lock: Final = ZCLAttributeDef(
            id=CHILD_LOCK, type=t.uint8_t, is_manufacturer_specific=True
        )
        away_preset_temperature: Final = ZCLAttributeDef(
            id=AWAY_PRESET_TEMPERATURE, type=t.uint32_t, is_manufacturer_specific=True
        )
        window_open: Final = ZCLAttributeDef(
            id=WINDOW_OPEN, type=t.uint8_t, is_manufacturer_specific=True
        )
        calibrated: Final = ZCLAttributeDef(
            id=CALIBRATED, type=t.uint8_t, is_manufacturer_specific=True
        )
        schedule: Final = ZCLAttributeDef(
            id=SCHEDULE, type=t.uint8_t, is_manufacturer_specific=True
        )
        schedule_settings: Final = ZCLAttributeDef(
            id=SCHEDULE_SETTINGS, type=ScheduleSettings, is_manufacturer_specific=True
        )
        sensor: Final = ZCLAttributeDef(
            id=SENSOR, type=t.uint8_t, is_manufacturer_specific=True
        )
        battery_percentage: Final = ZCLAttributeDef(
            id=BATTERY_PERCENTAGE, type=t.uint8_t, is_manufacturer_specific=True
        )

    def _update_attribute(self, attrid, value):
        self.debug("Updating attribute on Xiaomi cluster %s with %s", attrid, value)
        if attrid == BATTERY_PERCENTAGE:
            self.endpoint.power.battery_percent_reported(value)
        elif attrid == SYSTEM_MODE:
            # update ZCL system_mode attribute (e.g. on attribute reports)
            self.endpoint.thermostat.update_attribute(
                ZCL_SYSTEM_MODE, XIAOMI_SYSTEM_MODE_MAP[value]
            )
        elif attrid == HEARTBEAT:
            self._handle_heartbeat(value)
        elif attrid == PRESET:
            # Check for setup mode (preset=3)
            if value == Preset.Setup:
                self.debug("Device is in setup mode (E11)")
        super()._update_attribute(attrid, value)

    def _handle_heartbeat(self, value: bytes) -> None:
        """Handle heartbeat message and update related clusters."""
        heartbeat_data = _parse_heartbeat(value)
        self.debug("Parsed heartbeat data: %s", heartbeat_data)

        # Update device temperature
        if HEARTBEAT_DEVICE_TEMPERATURE in heartbeat_data:
            device_temp = heartbeat_data[HEARTBEAT_DEVICE_TEMPERATURE]
            # Device temperature is in degrees Celsius, ZCL expects centidegrees
            self.endpoint.device_temperature.update_attribute(
                DeviceTemperature.AttributeDefs.current_temperature.id,
                device_temp * 100,
            )

        # Update local temperature on thermostat
        if HEARTBEAT_LOCAL_TEMPERATURE in heartbeat_data:
            local_temp = heartbeat_data[HEARTBEAT_LOCAL_TEMPERATURE]
            # Temperature is already in centidegrees from heartbeat
            self.endpoint.thermostat.update_attribute(
                Thermostat.AttributeDefs.local_temperature.id,
                local_temp,
            )

        # Update battery
        if HEARTBEAT_BATTERY in heartbeat_data:
            battery = heartbeat_data[HEARTBEAT_BATTERY]
            self.endpoint.power.battery_percent_reported(battery)

        # Update preset (and detect setup mode)
        if HEARTBEAT_PRESET in heartbeat_data:
            preset = heartbeat_data[HEARTBEAT_PRESET]
            if preset == Preset.Setup:
                self.debug("Device is in setup mode (E11) from heartbeat")
            self.update_attribute(PRESET, preset)

        # Update valve alarm
        if HEARTBEAT_VALVE_ALARM in heartbeat_data:
            valve_alarm = heartbeat_data[HEARTBEAT_VALVE_ALARM]
            self.update_attribute(VALVE_ALARM, 1 if valve_alarm == 1 else 0)

        # Store power outage count for reference
        if HEARTBEAT_POWER_OUTAGE_COUNT in heartbeat_data:
            power_outage_count = heartbeat_data[HEARTBEAT_POWER_OUTAGE_COUNT] - 1
            self.debug("Power outage count: %s", power_outage_count)

        # Update firmware version on Basic cluster (standard ZCL attribute)
        if HEARTBEAT_FIRMWARE_VERSION in heartbeat_data:
            fw_version = heartbeat_data[HEARTBEAT_FIRMWARE_VERSION]
            version_str = str(fw_version)
            self.debug("Firmware version: %s", version_str)
            self.endpoint.basic.update_attribute(
                Basic.AttributeDefs.sw_build_id.id,
                version_str,
            )

    async def read_attributes(
        self,
        attributes: list[int | str],
        allow_cache: bool = False,
        only_cache: bool = False,
        manufacturer: int | t.uint16_t | None = None,
    ):
        """Read attributes with Xiaomi manufacturer code."""
        if manufacturer is None:
            manufacturer = XIAOMI_MANUFACTURER_CODE
        return await super().read_attributes(
            attributes, allow_cache, only_cache, manufacturer
        )

    async def write_attributes(
        self, attributes: dict[str | int, Any], manufacturer: int | None = None
    ) -> list:
        """Write attributes with Xiaomi manufacturer code."""
        if manufacturer is None:
            manufacturer = XIAOMI_MANUFACTURER_CODE

        attrs_to_write = {}
        for attr, value in attributes.items():
            # Resolve attribute name to ID if needed
            if isinstance(attr, str):
                attr_def = self.attributes_by_name.get(attr)
                if attr_def:
                    attr = attr_def.id
                else:
                    self.debug("Unknown attribute name: %s", attr)
                    continue

            # Handle calibrate trigger specially - writing 1 triggers calibration
            if attr == CALIBRATE:
                attrs_to_write[attr] = t.uint8_t(1)
            # Handle away_preset_temperature - value already in centidegrees from Number entity
            elif attr == AWAY_PRESET_TEMPERATURE:
                attrs_to_write[attr] = t.uint32_t(int(value))
            else:
                attrs_to_write[attr] = value

        return await super().write_attributes(attrs_to_write, manufacturer)


(
    QuirkBuilder(LUMI, "lumi.airrtc.agl001")
    .replaces(ThermostatCluster)
    .replaces(AqaraThermostatSpecificCluster)
    .replaces(XiaomiPowerConfiguration)
    .adds(LocalDeviceTemperatureCluster)
    # Complete entity definitions for this device.
    # Note: ZHA currently has legacy hardcoded entities for this device which may
    # cause duplicates. Those should be removed from ZHA in a follow-up PR.
    #
    # Switches
    .switch(
        AqaraThermostatSpecificCluster.AttributeDefs.child_lock.name,
        AqaraThermostatSpecificCluster.cluster_id,
        translation_key="child_lock",
        fallback_name="Child lock",
    )
    .switch(
        AqaraThermostatSpecificCluster.AttributeDefs.window_detection.name,
        AqaraThermostatSpecificCluster.cluster_id,
        translation_key="window_detection",
        fallback_name="Window detection",
    )
    .switch(
        AqaraThermostatSpecificCluster.AttributeDefs.valve_detection.name,
        AqaraThermostatSpecificCluster.cluster_id,
        translation_key="valve_detection",
        fallback_name="Valve detection",
    )
    .switch(
        AqaraThermostatSpecificCluster.AttributeDefs.schedule.name,
        AqaraThermostatSpecificCluster.cluster_id,
        translation_key="schedule",
        fallback_name="Schedule",
    )
    # Binary sensors
    .binary_sensor(
        AqaraThermostatSpecificCluster.AttributeDefs.valve_alarm.name,
        AqaraThermostatSpecificCluster.cluster_id,
        device_class=BinarySensorDeviceClass.PROBLEM,
        translation_key="valve_alarm",
        fallback_name="Valve alarm",
    )
    .binary_sensor(
        AqaraThermostatSpecificCluster.AttributeDefs.window_open.name,
        AqaraThermostatSpecificCluster.cluster_id,
        device_class=BinarySensorDeviceClass.WINDOW,
        translation_key="window_open",
        fallback_name="Window open",
    )
    .binary_sensor(
        AqaraThermostatSpecificCluster.AttributeDefs.calibrated.name,
        AqaraThermostatSpecificCluster.cluster_id,
        entity_type=EntityType.DIAGNOSTIC,
        translation_key="calibrated",
        fallback_name="Calibrated",
    )
    # Selects (enums)
    .enum(
        AqaraThermostatSpecificCluster.AttributeDefs.preset.name,
        Preset,
        AqaraThermostatSpecificCluster.cluster_id,
        translation_key="preset",
        fallback_name="Preset",
    )
    .enum(
        AqaraThermostatSpecificCluster.AttributeDefs.sensor.name,
        SensorMode,
        AqaraThermostatSpecificCluster.cluster_id,
        translation_key="sensor_mode",
        fallback_name="Sensor mode",
    )
    # Number
    .number(
        AqaraThermostatSpecificCluster.AttributeDefs.away_preset_temperature.name,
        AqaraThermostatSpecificCluster.cluster_id,
        min_value=5,
        max_value=30,
        step=0.5,
        unit=UnitOfTemperature.CELSIUS,
        multiplier=0.01,
        device_class=NumberDeviceClass.TEMPERATURE,
        translation_key="away_preset_temperature",
        fallback_name="Away preset temperature",
    )
    # Button
    .write_attr_button(
        AqaraThermostatSpecificCluster.AttributeDefs.calibrate.name,
        1,
        AqaraThermostatSpecificCluster.cluster_id,
        entity_type=EntityType.CONFIG,
        translation_key="calibrate",
        fallback_name="Calibrate",
    )
    .add_to_registry()
)
