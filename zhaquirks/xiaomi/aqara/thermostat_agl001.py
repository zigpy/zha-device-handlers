"""Aqara E1 Radiator Thermostat Quirk."""

from __future__ import annotations

from functools import reduce
import math
import struct
import time
from typing import Any, Final

import zigpy.types as t
from zigpy.typing import UNDEFINED, UndefinedType
from zigpy.zcl import ClusterType, foundation
from zigpy.zcl.clusters.general import Ota
from zigpy.zcl.clusters.hvac import Thermostat
from zigpy.zcl.foundation import ZCLAttributeDef

from zhaquirks.builder import (
    BinarySensorDeviceClass,
    EntityType,
    NumberDeviceClass,
    QuirkBuilder,
    UnitOfTemperature,
)
from zhaquirks.clusters import CustomCluster
from zhaquirks.xiaomi import (
    LUMI,
    XiaomiAqaraE1Cluster,
    XiaomiCustomDeviceV2,
    XiaomiPowerConfiguration,
)

ZCL_SYSTEM_MODE = Thermostat.attributes_by_name["system_mode"].id

XIAOMI_SYSTEM_MODE_MAP = {
    0: Thermostat.SystemMode.Off,
    1: Thermostat.SystemMode.Heat,
}

SYSTEM_MODE = 0x0271
PRESET = 0x0272
WINDOW_DETECTION = 0x0273
VALVE_DETECTION = 0x0274
VALVE_ALARM = 0x0275
CHILD_LOCK = 0x0277
AWAY_PRESET_TEMPERATURE = 0x0279
WINDOW_OPEN = 0x027A
CALIBRATED = 0x027B
SCHEDULE = 0x027D
SCHEDULE_SETTINGS = 0x0276
SENSOR = 0x027E
BATTERY_PERCENTAGE = 0x040A
LUMI_COMMAND = 0xFFF2
# Not a device attribute: holds the last external temperature sent to the device
EXTERNAL_TEMPERATURE = 0x1392

XIAOMI_CLUSTER_ID = 0xFCC0

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


# Placeholder ID of the "virtual" sensor the thermostat is linked to for external
# temperature input, as used by the Aqara hub and Zigbee2MQTT
EXTERNAL_SENSOR_ID = bytes.fromhex("00158d00019d1b98")
EXTERNAL_TEMPERATURE_MIN = 0
EXTERNAL_TEMPERATURE_MAX = 5500


class AqaraThermostatSensor(t.enum8):
    """Temperature sensor used by the thermostat."""

    Internal = 0x00
    External = 0x01


class AqaraThermostatPreset(t.enum8):
    """Thermostat preset."""

    Manual = 0x00
    Auto = 0x01
    Away = 0x02


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
        attributes: list[int | str | foundation.ZCLAttributeDef],
        **kwargs,
    ) -> Any:
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
                [SYSTEM_MODE], **kwargs
            )
            # convert Xiaomi system_mode to ZCL attribute
            if SYSTEM_MODE in successful_r:
                mapped_value = XIAOMI_SYSTEM_MODE_MAP[successful_r.pop(SYSTEM_MODE)]
                successful_r[ZCL_SYSTEM_MODE] = mapped_value
                # Update the thermostat cluster's cache
                self._update_attribute(ZCL_SYSTEM_MODE, mapped_value)
        # read remaining attributes from thermostat cluster
        if remaining_attributes:
            remaining_result = await super().read_attributes(
                remaining_attributes, **kwargs
            )
            successful_r.update(remaining_result[0])
            failed_r.update(remaining_result[1])
        return successful_r, failed_r

    async def write_attributes(
        self,
        attributes: dict[str | int | foundation.ZCLAttributeDef, Any],
        **kwargs,
    ) -> list[list[foundation.WriteAttributesStatusRecord]]:
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
                {SYSTEM_MODE: min(int(system_mode_value), 1)}, **kwargs
            )
            # Update the thermostat cluster's cache
            self._update_attribute(ZCL_SYSTEM_MODE, system_mode_value)

        # write remaining attributes to thermostat cluster
        if remaining_attributes:
            result += await super().write_attributes(remaining_attributes, **kwargs)
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


def _lumi_command(counter: int, action: int, params: bytes) -> bytes:
    """Build a Lumi command frame written to the `0xFFF2` attribute."""
    header = bytes([0xAA, 0x71, len(params) + 3, 0x44, counter])
    integrity = (512 - sum(header)) & 0xFF
    return header + bytes([integrity, action, 0x41, len(params)]) + params


def _sensor_mode_commands(sensor: AqaraThermostatSensor, ieee: t.EUI64) -> list[bytes]:
    """Build the two commands linking or unlinking the external temperature sensor."""
    device = bytes.fromhex(str(ieee).replace(":", ""))
    timestamp = struct.pack(">I", int(time.time()))

    if sensor == AqaraThermostatSensor.External:
        params1 = (
            timestamp
            + b"\x3d\x04"
            + device
            + EXTERNAL_SENSOR_ID
            + bytes(
                [
                    0x00, 0x01, 0x00, 0x55, 0x13, 0x0A, 0x02, 0x00,
                    0x00, 0x64, 0x04, 0xCE, 0xC2, 0xB6, 0xC8, 0x00,
                    0x00, 0x00, 0x00, 0x00, 0x01, 0x3D, 0x64, 0x65,
                ]
            )
        )  # fmt: skip
        params2 = (
            timestamp
            + b"\x3d\x05"
            + device
            + EXTERNAL_SENSOR_ID
            + bytes(
                [
                    0x08, 0x00, 0x07, 0xFD, 0x16, 0x0A, 0x02, 0x0A, 0xC9,
                    0xE8, 0xB1, 0xB8, 0xD4, 0xDA, 0xCF, 0xDF, 0xC0, 0xEB,
                    0x00, 0x00, 0x00, 0x00, 0x00, 0x01, 0x3D, 0x04, 0x65,
                ]
            )
        )  # fmt: skip
        action = 0x02
    else:
        params1 = timestamp + b"\x3d\x05" + device + bytes(12)
        params2 = timestamp + b"\x3d\x04" + device + bytes(12)
        action = 0x04

    return [
        _lumi_command(0x12, action, params1),
        _lumi_command(0x13, action, params2),
    ]


def _external_temperature_command(temperature: int) -> bytes:
    """Build the command reporting an external temperature, in 0.01 °C."""
    params = EXTERNAL_SENSOR_ID + b"\x00\x01\x00\x55" + struct.pack(">f", temperature)
    return _lumi_command(0x12, 0x05, params)


class AqaraThermostatSpecificCluster(XiaomiAqaraE1Cluster):
    """Aqara manufacturer specific settings."""

    class AttributeDefs(XiaomiAqaraE1Cluster.AttributeDefs):
        """Attribute definitions."""

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
        lumi_command: Final = ZCLAttributeDef(
            id=LUMI_COMMAND, type=t.LVBytes, is_manufacturer_specific=True
        )
        external_temperature: Final = ZCLAttributeDef(
            id=EXTERNAL_TEMPERATURE, type=t.int16s, is_manufacturer_specific=True
        )

    async def read_attributes(
        self,
        attributes: list[int | str | foundation.ZCLAttributeDef],
        *args,
        **kwargs,
    ) -> Any:
        """Answer reads of the external temperature locally."""
        local = [
            attr
            for attr in attributes
            if self.find_attribute(attr).id == EXTERNAL_TEMPERATURE
        ]
        if not local:
            return await super().read_attributes(attributes, *args, **kwargs)

        remaining = [attr for attr in attributes if attr not in local]
        successful_r, failed_r = {}, {}
        if remaining:
            successful_r, failed_r = await super().read_attributes(
                remaining, *args, **kwargs
            )

        value = self.get(EXTERNAL_TEMPERATURE)
        for attr in local:
            if value is not None:
                successful_r[attr] = value
            else:
                failed_r[attr] = foundation.Status.UNSUPPORTED_ATTRIBUTE
        return successful_r, failed_r

    async def write_attributes(
        self,
        attributes: dict[str | int | foundation.ZCLAttributeDef, Any],
        manufacturer: int | UndefinedType | None = UNDEFINED,
        **kwargs,
    ) -> list[list[foundation.WriteAttributesStatusRecord]]:
        """Send sensor selection and external temperature as Lumi commands."""
        records = []
        remaining_attributes = {}

        for attr, value in attributes.items():
            attr_id = self.find_attribute(attr).id
            if attr_id == SENSOR:
                if value not in list(AqaraThermostatSensor):
                    raise ValueError(f"Invalid temperature sensor: {value!r}")
                sensor = AqaraThermostatSensor(value)
                commands = _sensor_mode_commands(sensor, self.endpoint.device.ieee)
                status = await self._write_lumi_commands(commands, manufacturer)
                if status == foundation.Status.SUCCESS:
                    self._update_attribute(SENSOR, sensor)
                    if sensor == AqaraThermostatSensor.Internal:
                        await self._read_local_temperature()
            elif attr_id == EXTERNAL_TEMPERATURE:
                temperature = int(value)
                if not (
                    EXTERNAL_TEMPERATURE_MIN <= temperature <= EXTERNAL_TEMPERATURE_MAX
                ):
                    raise ValueError(
                        f"External temperature must be between"
                        f" {EXTERNAL_TEMPERATURE_MIN} and {EXTERNAL_TEMPERATURE_MAX}"
                        f" (0.01 °C), got {temperature}"
                    )
                command = _external_temperature_command(temperature)
                status = await self._write_lumi_commands([command], manufacturer)
                if status == foundation.Status.SUCCESS:
                    self._update_attribute(EXTERNAL_TEMPERATURE, temperature)
            else:
                remaining_attributes[attr] = value
                continue

            records.append(
                foundation.WriteAttributesStatusRecord(status=status, attrid=attr_id)
            )

        if remaining_attributes:
            result = await super().write_attributes(
                remaining_attributes, manufacturer, **kwargs
            )
            records.extend(result[0])
        return [records]

    async def _read_local_temperature(self) -> None:
        """Read the internal temperature again after leaving the external sensor."""
        try:
            await self.endpoint.thermostat.read_attributes(
                [Thermostat.AttributeDefs.local_temperature.name]
            )
        except Exception as exc:  # noqa: BLE001
            self.debug("Failed to read the local temperature: %r", exc)

    async def _write_lumi_commands(
        self, commands: list[bytes], manufacturer: int | UndefinedType | None
    ) -> foundation.Status:
        """Write Lumi commands in order, stopping at the first failure."""
        for command in commands:
            result = await super().write_attributes(
                {LUMI_COMMAND: command}, manufacturer, update_cache=False
            )
            for record in result[0]:
                if record.status != foundation.Status.SUCCESS:
                    return record.status
        return foundation.Status.SUCCESS

    def _update_attribute(self, attrid, value):
        self.debug("Updating attribute on Xiaomi cluster %s with %s", attrid, value)
        if attrid == SENSOR and value == 2:
            # Also reported while the external temperature input is in use, which
            # Zigbee2MQTT treats the same as an external sensor
            value = AqaraThermostatSensor.External
        if attrid == BATTERY_PERCENTAGE:
            self.endpoint.power.battery_percent_reported(value)
        elif attrid == SYSTEM_MODE:
            # update ZCL system_mode attribute (e.g. on attribute reports)
            self.endpoint.thermostat.update_attribute(
                ZCL_SYSTEM_MODE, XIAOMI_SYSTEM_MODE_MAP[value]
            )
        super()._update_attribute(attrid, value)


# Unique ID suffixes keep the `{ieee}-1-64704-<attribute>` IDs of the entities ZHA used
# to create for this device (cluster ID 0xFCC0 = 64704).
(
    QuirkBuilder(LUMI, "lumi.airrtc.agl001")
    .zigpy_device_class(XiaomiCustomDeviceV2)
    .replaces(ThermostatCluster)
    .replaces(ThermostatCluster, cluster_type=ClusterType.Client)
    .replaces(XiaomiPowerConfiguration)
    .replaces(AqaraThermostatSpecificCluster)
    .replaces(AqaraThermostatSpecificCluster, cluster_type=ClusterType.Client)
    .adds(Ota, cluster_type=ClusterType.Client)
    .switch(
        attribute_name=AqaraThermostatSpecificCluster.AttributeDefs.window_detection.name,
        cluster_id=AqaraThermostatSpecificCluster.cluster_id,
        unique_id_suffix="64704-window_detection",
        translation_key="window_detection",
        fallback_name="Open window detection",
    )
    .switch(
        attribute_name=AqaraThermostatSpecificCluster.AttributeDefs.valve_detection.name,
        cluster_id=AqaraThermostatSpecificCluster.cluster_id,
        unique_id_suffix="64704-valve_detection",
        translation_key="valve_detection",
        fallback_name="Valve detection",
    )
    .switch(
        attribute_name=AqaraThermostatSpecificCluster.AttributeDefs.child_lock.name,
        cluster_id=AqaraThermostatSpecificCluster.cluster_id,
        unique_id_suffix="64704-child_lock",
        translation_key="child_lock",
        fallback_name="Child lock",
    )
    .enum(
        attribute_name=AqaraThermostatSpecificCluster.AttributeDefs.preset.name,
        enum_class=AqaraThermostatPreset,
        cluster_id=AqaraThermostatSpecificCluster.cluster_id,
        unique_id_suffix="64704-preset",
        translation_key="preset",
        fallback_name="Preset",
    )
    .number(
        attribute_name=AqaraThermostatSpecificCluster.AttributeDefs.away_preset_temperature.name,
        cluster_id=AqaraThermostatSpecificCluster.cluster_id,
        min_value=5,
        max_value=30,
        multiplier=0.01,
        unit=UnitOfTemperature.CELSIUS,
        mode="slider",
        unique_id_suffix="64704-away_preset_temperature",
        translation_key="away_preset_temperature",
        fallback_name="Away preset temperature",
    )
    .binary_sensor(
        attribute_name=AqaraThermostatSpecificCluster.AttributeDefs.window_open.name,
        cluster_id=AqaraThermostatSpecificCluster.cluster_id,
        entity_type=EntityType.STANDARD,
        device_class=BinarySensorDeviceClass.WINDOW,
        unique_id_suffix="64704-window_open",
        fallback_name="Window open",
    )
    .binary_sensor(
        attribute_name=AqaraThermostatSpecificCluster.AttributeDefs.valve_alarm.name,
        cluster_id=AqaraThermostatSpecificCluster.cluster_id,
        entity_type=EntityType.STANDARD,
        device_class=BinarySensorDeviceClass.PROBLEM,
        unique_id_suffix="64704-valve_alarm",
        translation_key="valve_alarm",
        fallback_name="Valve alarm",
    )
    .binary_sensor(
        attribute_name=AqaraThermostatSpecificCluster.AttributeDefs.calibrated.name,
        cluster_id=AqaraThermostatSpecificCluster.cluster_id,
        entity_type=EntityType.DIAGNOSTIC,
        unique_id_suffix="64704-calibrated",
        translation_key="calibrated",
        fallback_name="Calibrated",
    )
    .switch(
        attribute_name=AqaraThermostatSpecificCluster.AttributeDefs.sensor.name,
        cluster_id=AqaraThermostatSpecificCluster.cluster_id,
        on_value=AqaraThermostatSensor.External,
        off_value=AqaraThermostatSensor.Internal,
        unique_id_suffix="64704-sensor",
        translation_key="external_temperature_sensor",
        fallback_name="External temperature sensor",
    )
    .number(
        attribute_name=AqaraThermostatSpecificCluster.AttributeDefs.external_temperature.name,
        cluster_id=AqaraThermostatSpecificCluster.cluster_id,
        min_value=EXTERNAL_TEMPERATURE_MIN / 100,
        max_value=EXTERNAL_TEMPERATURE_MAX / 100,
        step=0.1,
        multiplier=0.01,
        unit=UnitOfTemperature.CELSIUS,
        mode="box",
        device_class=NumberDeviceClass.TEMPERATURE,
        unique_id_suffix="64704-external_temperature",
        translation_key="external_temperature_sensor_value",
        fallback_name="External temperature sensor value",
    )
    .add_to_registry()
)
