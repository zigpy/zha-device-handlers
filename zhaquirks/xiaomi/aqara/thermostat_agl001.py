"""Aqara E1 Radiator Thermostat Quirk."""

from __future__ import annotations

import math
import struct
from typing import Any, ClassVar, Final

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
from zigpy.quirks.v2.homeassistant import EntityPlatform, EntityType, UnitOfTemperature
from zigpy.quirks.v2.homeassistant.binary_sensor import BinarySensorDeviceClass
from zigpy.quirks.v2.homeassistant.number import NumberDeviceClass
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import DeviceTemperature
from zigpy.zcl.clusters.hvac import Thermostat

from zhaquirks import LocalDataCluster
from zhaquirks.xiaomi import (
    HEARTBEAT_HEATING_SETPOINT,
    HEARTBEAT_LOCAL_TEMPERATURE,
    HEARTBEAT_PRESET,
    HEARTBEAT_VALVE_ALARM,
    LUMI,
    XIAOMI_AQARA_ATTRIBUTE_E1,
    XiaomiAqaraE1Cluster,
    XiaomiPowerConfiguration,
)

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

XIAOMI_MANUFACTURER_CODE = 0x115F

# Schedule settings format constants
SCHEDULE_MAGIC_BYTE = 0x04


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


# Schedule and validation constants
MINUTES_PER_DAY = 24 * 60
MIN_TEMPERATURE = 5
MAX_TEMPERATURE = 30
MIN_EVENT_DURATION_MINUTES = 60

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
    _CONSTANT_ATTRIBUTES: ClassVar[dict[int, Any]] = {
        Thermostat.attributes_by_name[
            "ctrl_sequence_of_oper"
        ].id: Thermostat.ControlSequenceOfOperation.Heating_Only
    }

    # Attribute IDs for special handling
    _RUNNING_STATE_ATTR = Thermostat.AttributeDefs.running_state.id
    _LOCAL_TEMP_ATTR = Thermostat.AttributeDefs.local_temperature.id
    _SETPOINT_ATTR = Thermostat.AttributeDefs.occupied_heating_setpoint.id

    def _update_running_state(self):
        """Update running_state based on current temperature and setpoint.

        Called after setpoint or system_mode changes to keep running_state in sync.
        """
        # Get current values from cache
        local_temp = self._attr_cache.get(self._LOCAL_TEMP_ATTR)
        setpoint = self._attr_cache.get(self._SETPOINT_ATTR)

        # Get system_mode from OppleCluster
        opple_cluster = self.endpoint.opple_cluster
        system_mode = opple_cluster._attr_cache.get(SYSTEM_MODE, SystemMode.Heat)

        # Can only calculate if we have both temperature and setpoint
        if local_temp is None or setpoint is None:
            return

        # Calculate running_state
        if system_mode == SystemMode.Off:
            running_state = 0  # Idle
        elif setpoint > local_temp:
            running_state = Thermostat.RunningState.Heat_State_On
        else:
            running_state = 0  # Idle

        # Update the attribute
        self.update_attribute(self._RUNNING_STATE_ATTR, running_state)
        self.debug(
            "Updated running_state to %s (temp=%s, setpoint=%s, mode=%s)",
            running_state,
            local_temp,
            setpoint,
            system_mode,
        )

    async def read_attributes(
        self,
        attributes: list[int | str | foundation.ZCLAttributeDef],
        **kwargs,
    ) -> Any:
        """Pass reading attributes to Xiaomi cluster if applicable."""
        successful_r, failed_r = {}, {}
        remaining_attributes = attributes.copy()

        # Handle running_state - device doesn't support it natively, we simulate it
        # from heartbeat data. Return cached value or default to Idle.
        running_state_requested = (
            self._RUNNING_STATE_ATTR in attributes or "running_state" in attributes
        )
        if running_state_requested:
            if self._RUNNING_STATE_ATTR in attributes:
                remaining_attributes.remove(self._RUNNING_STATE_ATTR)
            if "running_state" in attributes:
                remaining_attributes.remove("running_state")
            # Return cached value (set by heartbeat) or default to Idle (0)
            cached_state = self._attr_cache.get(self._RUNNING_STATE_ATTR, 0)
            successful_r[self._RUNNING_STATE_ATTR] = cached_state

        # read system_mode from Xiaomi cluster (can be numeric or string)
        if ZCL_SYSTEM_MODE in attributes or "system_mode" in attributes:
            self.debug("Passing 'system_mode' read to Xiaomi cluster")

            if ZCL_SYSTEM_MODE in attributes:
                remaining_attributes.remove(ZCL_SYSTEM_MODE)
            if "system_mode" in attributes:
                remaining_attributes.remove("system_mode")

            opple_r, opple_f = await self.endpoint.opple_cluster.read_attributes(
                [SYSTEM_MODE], **kwargs
            )
            failed_r.update(opple_f)
            # convert Xiaomi system_mode to ZCL attribute
            if SYSTEM_MODE in opple_r:
                mapped_value = XIAOMI_SYSTEM_MODE_MAP[opple_r.pop(SYSTEM_MODE)]
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
            # Update running_state after system_mode change
            self._update_running_state()

        # write remaining attributes to thermostat cluster
        if remaining_attributes:
            result += await super().write_attributes(remaining_attributes, **kwargs)
            # Update running_state if setpoint was changed
            if (
                self._SETPOINT_ATTR in remaining_attributes
                or "occupied_heating_setpoint" in remaining_attributes
            ):
                self._update_running_state()
        return result


class ScheduleEvent:
    """Schedule event object."""

    _is_next_day: bool = False
    _time: int
    _temp: float

    def __init__(self, value: bytes | str, is_next_day: bool = False) -> None:
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
    def _verify_buffer_len(buf: bytes) -> None:
        if len(buf) != 6:
            raise ValueError("Buffer size must equal 6")

    @staticmethod
    def _read_time_from_buf(buf: bytes) -> int:
        time = struct.unpack_from(">H", buf, offset=0)[0]
        time &= ~NEXT_DAY_FLAG
        return time

    @staticmethod
    def _parse_time(string: str) -> int:
        parts = string.split(":")
        if len(parts) != 2:
            raise ValueError("Time must contain ':' separator")

        hours = int(parts[0])
        minutes = int(parts[1])

        return hours * 60 + minutes

    @staticmethod
    def _read_temp_from_buf(buf: bytes) -> float:
        return struct.unpack_from(">H", buf, offset=4)[0] / 100

    @staticmethod
    def _parse_temp(string: str) -> float:
        return float(string)

    @staticmethod
    def _validate_time(time: int) -> None:
        if not 0 < time <= MINUTES_PER_DAY:
            raise ValueError("Time must be between 00:00 and 23:59")

    @staticmethod
    def _validate_temp(temp: float) -> None:
        if not MIN_TEMPERATURE <= temp <= MAX_TEMPERATURE:
            msg = (
                f"Temperature must be between "
                f"{MIN_TEMPERATURE} and {MAX_TEMPERATURE} °C"
            )
            raise ValueError(msg)
        if (temp * 10) % 5 != 0:
            raise ValueError("Temperature must be whole or half degrees")

    def _write_time_to_buf(self, buf: bytearray) -> None:
        time = self._time
        if self._is_next_day:
            time |= NEXT_DAY_FLAG
        struct.pack_into(">H", buf, 0, time)

    def _write_temp_to_buf(self, buf: bytearray) -> None:
        struct.pack_into(">H", buf, 4, int(self._temp * 100))

    def is_next_day(self) -> bool:
        """Return if event is on the next day."""
        return self._is_next_day

    def set_next_day(self, is_next_day: bool) -> None:
        """Set if event is on the next day."""
        self._is_next_day = is_next_day

    def get_time(self) -> int:
        """Return event time."""
        return self._time

    def __str__(self) -> str:
        """Return event as string."""
        hours = math.floor(self._time / 60)
        minutes = f"{self._time % 60:0>2}"
        temp = f"{self._temp:.1f}"
        return f"{hours}:{minutes},{temp}"

    def serialize(self) -> bytes:
        """Serialize event to bytes."""
        result = bytearray(6)
        self._write_time_to_buf(result)
        self._write_temp_to_buf(result)
        return result


class ScheduleSettings(t.LVBytes):
    """Schedule settings object."""

    def __new__(cls, value: bytes | str):
        """Create ScheduleSettings object from bytes or string."""
        day_selection: list[str]
        events: list[ScheduleEvent]

        if isinstance(value, bytes):
            ScheduleSettings._verify_buffer_len(value)
            ScheduleSettings._verify_magic_byte(value)
            day_selection = ScheduleSettings._read_day_selection(value)
            events = [ScheduleSettings._read_event(value, i) for i in range(4)]
        elif isinstance(value, str):
            groups = value.split("|")
            ScheduleSettings._verify_string(groups)
            day_selection = ScheduleSettings._read_day_selection(groups[0])
            events = [ScheduleSettings._read_event(groups[i + 1], i) for i in range(4)]
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
    def _verify_buffer_len(buf: bytes) -> None:
        if len(buf) != 26:
            raise ValueError("Buffer size must equal 26")

    @staticmethod
    def _verify_magic_byte(buf: bytes) -> None:
        if struct.unpack_from("c", buf, offset=0)[0][0] != SCHEDULE_MAGIC_BYTE:
            raise ValueError(f"Magic byte must be equal to {SCHEDULE_MAGIC_BYTE:#x}")

    @staticmethod
    def _verify_string(groups: list[str]) -> None:
        if len(groups) != 5:
            raise ValueError("There must be 5 groups in a string")
        days = groups[0].split(",")
        ScheduleSettings._verify_day_selection_in_str(days)

    @staticmethod
    def _verify_day_selection_in_str(days: list[str]) -> None:
        if not 1 <= len(days) <= 7:
            raise ValueError("Number of days selected must be between 1 and 7")
        if len(days) != len(set(days)):
            raise ValueError("Duplicate day names present")
        for d in days:
            if d not in DAYS_MAP:
                msg = (
                    f"String: {d} is not a valid day name, "
                    "valid names: mon, tue, wed, thu, fri, sat, sun"
                )
                raise ValueError(msg)

    @staticmethod
    def _read_day_selection(value: bytes | str) -> list[str]:
        day_selection: list[str] = []
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
    def _read_event(value: bytes | str, index: int) -> ScheduleEvent:
        if isinstance(value, bytes):
            event_buf = value[2 + index * 6 : 8 + index * 6]
            return ScheduleEvent(event_buf)
        return ScheduleEvent(value)

    @staticmethod
    def _verify_event_durations(events: list[ScheduleEvent]) -> None:
        prev_time = events[0].get_time()
        durations: list[int] = []
        for i in range(1, 4):
            event = events[i]
            if event.is_next_day():
                durations.append(MINUTES_PER_DAY - prev_time + event.get_time())
            else:
                durations.append(event.get_time() - prev_time)
            prev_time = event.get_time()
        if any(d < MIN_EVENT_DURATION_MINUTES for d in durations):
            raise ValueError("The individual times must be at least 1 hour apart")
        if sum(durations) > MINUTES_PER_DAY:
            raise ValueError("The start and end times must be at most 24 hours apart")

    @staticmethod
    def _get_day_selection_byte(day_selection: list[str]) -> int:
        byte = 0x00
        for d in day_selection:
            byte |= DAYS_MAP[d]
        return byte

    def __str__(self) -> str:
        """Return ScheduleSettings as string."""
        day_selection = ScheduleSettings._read_day_selection(self)
        events: list[ScheduleEvent | None] = [None] * 4
        for i in range(4):
            events[i] = ScheduleSettings._read_event(self, i)
        result = ",".join(day_selection)
        for e in events:
            result += f"|{e}"
        return result


class LocalDeviceTemperatureCluster(LocalDataCluster, DeviceTemperature):
    """Device temperature cluster for internal TRV temperature."""

    _CONSTANT_ATTRIBUTES: ClassVar[dict[int, int]] = {
        DeviceTemperature.AttributeDefs.min_temp_experienced.id: -4000,
        DeviceTemperature.AttributeDefs.max_temp_experienced.id: 12500,
    }


class AqaraThermostatSpecificCluster(XiaomiAqaraE1Cluster):
    """Aqara manufacturer specific settings."""

    class AttributeDefs(XiaomiAqaraE1Cluster.AttributeDefs):
        """Attribute definitions."""

        calibrate: Final = foundation.ZCLAttributeDef(
            id=CALIBRATE, type=t.uint8_t, is_manufacturer_specific=True
        )
        system_mode: Final = foundation.ZCLAttributeDef(
            id=SYSTEM_MODE, type=t.uint8_t, is_manufacturer_specific=True
        )
        preset: Final = foundation.ZCLAttributeDef(
            id=PRESET, type=t.uint8_t, is_manufacturer_specific=True
        )
        window_detection: Final = foundation.ZCLAttributeDef(
            id=WINDOW_DETECTION, type=t.uint8_t, is_manufacturer_specific=True
        )
        valve_detection: Final = foundation.ZCLAttributeDef(
            id=VALVE_DETECTION, type=t.uint8_t, is_manufacturer_specific=True
        )
        valve_alarm: Final = foundation.ZCLAttributeDef(
            id=VALVE_ALARM, type=t.uint8_t, is_manufacturer_specific=True
        )
        child_lock: Final = foundation.ZCLAttributeDef(
            id=CHILD_LOCK, type=t.uint8_t, is_manufacturer_specific=True
        )
        away_preset_temperature: Final = foundation.ZCLAttributeDef(
            id=AWAY_PRESET_TEMPERATURE, type=t.uint32_t, is_manufacturer_specific=True
        )
        window_open: Final = foundation.ZCLAttributeDef(
            id=WINDOW_OPEN, type=t.uint8_t, is_manufacturer_specific=True
        )
        calibrated: Final = foundation.ZCLAttributeDef(
            id=CALIBRATED, type=t.uint8_t, is_manufacturer_specific=True
        )
        schedule: Final = foundation.ZCLAttributeDef(
            id=SCHEDULE, type=t.uint8_t, is_manufacturer_specific=True
        )
        schedule_settings: Final = foundation.ZCLAttributeDef(
            id=SCHEDULE_SETTINGS, type=ScheduleSettings, is_manufacturer_specific=True
        )
        sensor: Final = foundation.ZCLAttributeDef(
            id=SENSOR, type=t.uint8_t, is_manufacturer_specific=True
        )
        battery_percentage: Final = foundation.ZCLAttributeDef(
            id=BATTERY_PERCENTAGE, type=t.uint8_t, is_manufacturer_specific=True
        )

    def _update_attribute(self, attrid: int, value: Any) -> None:
        """Update attribute and handle manufacturer-specific logic."""
        self.debug("Updating attribute on Xiaomi cluster %s with %s", attrid, value)

        # Base class handles heartbeat parsing and standard attribute updates
        # (device_temperature, local_temperature, battery, firmware_version)
        super()._update_attribute(attrid, value)

        # Handle manufacturer-specific attributes from heartbeat
        if attrid == XIAOMI_AQARA_ATTRIBUTE_E1:
            # Re-parse to get manufacturer-specific attributes
            # (base class already did standard updates)
            from zhaquirks.xiaomi import _parse_tlv_heartbeat

            heartbeat_data = _parse_tlv_heartbeat(value)

            # Update preset (manufacturer-specific attribute)
            if HEARTBEAT_PRESET in heartbeat_data:
                preset = heartbeat_data[HEARTBEAT_PRESET]
                if preset == Preset.Setup:
                    self.debug("Device is in setup mode (E11)")
                self.update_attribute(PRESET, preset)

            # Update valve alarm (manufacturer-specific attribute)
            if HEARTBEAT_VALVE_ALARM in heartbeat_data:
                valve_alarm = heartbeat_data[HEARTBEAT_VALVE_ALARM]
                self.update_attribute(VALVE_ALARM, 1 if valve_alarm == 1 else 0)

            # Simulate running_state based on temperature difference
            # (device doesn't report this, so we derive it)
            if (
                HEARTBEAT_LOCAL_TEMPERATURE in heartbeat_data
                and HEARTBEAT_HEATING_SETPOINT in heartbeat_data
            ):
                local_temp = heartbeat_data[HEARTBEAT_LOCAL_TEMPERATURE]
                setpoint = heartbeat_data[HEARTBEAT_HEATING_SETPOINT]
                system_mode = self._attr_cache.get(SYSTEM_MODE, SystemMode.Heat)

                if system_mode == SystemMode.Off:
                    running_state = 0  # Idle
                elif setpoint > local_temp:
                    running_state = Thermostat.RunningState.Heat_State_On
                else:
                    running_state = 0  # Idle

                self.endpoint.thermostat.update_attribute(
                    Thermostat.AttributeDefs.running_state.id,
                    running_state,
                )

        elif attrid == BATTERY_PERCENTAGE:
            self.endpoint.power.battery_percent_reported(value)
        elif attrid == SYSTEM_MODE:
            # Update ZCL system_mode attribute (e.g. on attribute reports)
            self.endpoint.thermostat.update_attribute(
                ZCL_SYSTEM_MODE, XIAOMI_SYSTEM_MODE_MAP[value]
            )
            # Update running_state after system_mode change
            self.endpoint.thermostat._update_running_state()
        elif attrid == PRESET:
            # Check for setup mode (preset=3)
            if value == Preset.Setup:
                self.debug("Device is in setup mode (E11)")

    async def read_attributes(
        self,
        attributes: list[int | str | foundation.ZCLAttributeDef],
        **kwargs,
    ) -> Any:
        """Read attributes with Xiaomi manufacturer code."""
        if "manufacturer" not in kwargs or kwargs["manufacturer"] is None:
            kwargs["manufacturer"] = XIAOMI_MANUFACTURER_CODE
        return await super().read_attributes(attributes, **kwargs)

    async def write_attributes(
        self,
        attributes: dict[str | int | foundation.ZCLAttributeDef, Any],
        **kwargs,
    ) -> list[list[foundation.WriteAttributesStatusRecord]]:
        """Write attributes with Xiaomi manufacturer code."""
        if "manufacturer" not in kwargs or kwargs["manufacturer"] is None:
            kwargs["manufacturer"] = XIAOMI_MANUFACTURER_CODE

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

            # Handle calibrate trigger specially
            # Writing 1 triggers calibration
            if attr == CALIBRATE:
                attrs_to_write[attr] = t.uint8_t(1)
            # Handle away_preset_temperature
            # Value already in centidegrees from Number entity
            elif attr == AWAY_PRESET_TEMPERATURE:
                attrs_to_write[attr] = t.uint32_t(int(value))
            else:
                attrs_to_write[attr] = value

        return await super().write_attributes(attrs_to_write, **kwargs)


(
    QuirkBuilder(LUMI, "lumi.airrtc.agl001")
    .replaces(ThermostatCluster)
    .replaces(AqaraThermostatSpecificCluster)
    .replaces(XiaomiPowerConfiguration)
    .adds(LocalDeviceTemperatureCluster)
    # Complete entity definitions for this device.
    # unique_id_suffix values match legacy ZHA entity IDs for seamless migration
    # (prevents duplicate entities and preserves automations/dashboards).
    #
    # Switches
    .switch(
        AqaraThermostatSpecificCluster.AttributeDefs.child_lock.name,
        AqaraThermostatSpecificCluster.cluster_id,
        translation_key="child_lock",
        fallback_name="Child lock",
        unique_id_suffix="64704-child_lock",
    )
    .switch(
        AqaraThermostatSpecificCluster.AttributeDefs.window_detection.name,
        AqaraThermostatSpecificCluster.cluster_id,
        translation_key="window_detection",
        fallback_name="Open window detection",
        unique_id_suffix="64704-window_detection",
    )
    .switch(
        AqaraThermostatSpecificCluster.AttributeDefs.valve_detection.name,
        AqaraThermostatSpecificCluster.cluster_id,
        translation_key="valve_detection",
        fallback_name="Valve detection",
        unique_id_suffix="64704-valve_detection",
    )
    .switch(
        AqaraThermostatSpecificCluster.AttributeDefs.schedule.name,
        AqaraThermostatSpecificCluster.cluster_id,
        translation_key="schedule",
        fallback_name="Schedule",
        unique_id_suffix="64704-schedule",
    )
    # Binary sensors
    .binary_sensor(
        AqaraThermostatSpecificCluster.AttributeDefs.valve_alarm.name,
        AqaraThermostatSpecificCluster.cluster_id,
        device_class=BinarySensorDeviceClass.PROBLEM,
        translation_key="valve_alarm",
        fallback_name="Valve alarm",
        unique_id_suffix="64704-valve_alarm",
    )
    .binary_sensor(
        AqaraThermostatSpecificCluster.AttributeDefs.window_open.name,
        AqaraThermostatSpecificCluster.cluster_id,
        device_class=BinarySensorDeviceClass.WINDOW,
        translation_key="window_open",
        fallback_name="Window open",
        unique_id_suffix="64704-window_open",
    )
    .binary_sensor(
        AqaraThermostatSpecificCluster.AttributeDefs.calibrated.name,
        AqaraThermostatSpecificCluster.cluster_id,
        entity_type=EntityType.DIAGNOSTIC,
        translation_key="calibrated",
        fallback_name="Calibrated",
        unique_id_suffix="64704-calibrated",
    )
    # Sensors (enums - read-only)
    .enum(
        AqaraThermostatSpecificCluster.AttributeDefs.preset.name,
        Preset,
        AqaraThermostatSpecificCluster.cluster_id,
        # Read-only, device/schedule controls this
        entity_platform=EntityPlatform.SENSOR,
        entity_type=EntityType.STANDARD,
        translation_key="preset",
        fallback_name="Preset",
        unique_id_suffix="64704-preset",
    )
    # Selects (enums - user controllable)
    .enum(
        AqaraThermostatSpecificCluster.AttributeDefs.sensor.name,
        SensorMode,
        AqaraThermostatSpecificCluster.cluster_id,
        translation_key="sensor_mode",
        fallback_name="Sensor mode",
        unique_id_suffix="64704-sensor",
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
        unique_id_suffix="64704-away_preset_temperature",
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
