"""Rti-Tek eTRV-ZB02 Zigbee thermostatic radiator valve."""

from __future__ import annotations

import asyncio
import datetime as dt
import enum
from typing import Any, Final

import zigpy.types as t
from zigpy.zcl.clusters.general import Basic, Identify
from zigpy.zcl.clusters.hvac import SeqDayOfWeek, SeqMode, Thermostat
from zigpy.zcl.foundation import (
    BaseAttributeDefs,
    BaseCommandDefs,
    DataTypeId,
    Status,
    ZCLAttributeDef,
    ZCLCommandDef,
)

from zhaquirks.builder import (
    EntityType,
    NumberDeviceClass,
    QuirkBuilder,
    UnitOfTemperature,
    UnitOfTime,
)
from zhaquirks.builder.device import QuirkV2Device
from zhaquirks.clusters import CustomCluster

ETRV_ZB02_WEEKLY_SCHEDULE_MAX_PERIODS: Final = 12
ETRV_ZB02_WEEKLY_SCHEDULE_NULL_TIME: Final = 0xFFFF
ETRV_ZB02_WEEKLY_SCHEDULE_DISABLED_HOUR: Final = 0xFF
ETRV_ZB02_WEEKLY_SCHEDULE_DEFAULT_TEMPERATURE: Final = 2000
ETRV_ZB02_WEEKLY_SCHEDULE_DAY_ATTR: Final = 0xF100
ETRV_ZB02_WEEKLY_SCHEDULE_TIME_ATTRS: Final = {
    index: 0xF101 + index - 1 if index <= 6 else 0xF11B + (index - 7) * 4
    for index in range(1, ETRV_ZB02_WEEKLY_SCHEDULE_MAX_PERIODS + 1)
}
ETRV_ZB02_WEEKLY_SCHEDULE_TEMPERATURE_ATTRS: Final = {
    index: 0xF107 + index - 1 if index <= 6 else 0xF11C + (index - 7) * 4
    for index in range(1, ETRV_ZB02_WEEKLY_SCHEDULE_MAX_PERIODS + 1)
}
ETRV_ZB02_WEEKLY_SCHEDULE_HOUR_ATTRS: Final = {
    index: 0xF10D + index - 1 if index <= 6 else 0xF11D + (index - 7) * 4
    for index in range(1, ETRV_ZB02_WEEKLY_SCHEDULE_MAX_PERIODS + 1)
}
ETRV_ZB02_WEEKLY_SCHEDULE_MINUTE_ATTRS: Final = {
    index: 0xF113 + index - 1 if index <= 6 else 0xF11E + (index - 7) * 4
    for index in range(1, ETRV_ZB02_WEEKLY_SCHEDULE_MAX_PERIODS + 1)
}
ETRV_ZB02_TEMPORARY_MANUAL_TEMPERATURE_ATTR: Final = 0xF119


class EtrvZb02SystemMode(t.enum8):
    """System modes supported by the device."""

    Off = 0x00
    Auto = 0x01
    Manual = 0x04


class EtrvZb02ScreenBrightness(t.enum8):
    """Screen brightness values."""

    High = 0x00
    Medium = 0x01
    Low = 0x02


EtrvZb02ScreenDirection = enum.Enum(
    "EtrvZb02ScreenDirection",
    {"0 degrees": 0x00, "90 degrees": 0x03, "180 degrees": 0x01, "270 degrees": 0x02},
    type=t.uint8_t,
)


EtrvZb02ScreenDisplayDuration = enum.Enum(
    "EtrvZb02ScreenDisplayDuration",
    {"5 seconds": 5, "10 seconds": 10, "15 seconds": 15},
    type=t.uint16_t,
)


EtrvZb02TemperatureControlMode = enum.Enum(
    "EtrvZb02TemperatureControlMode",
    {"PID": 0x00, "ON-OFF": 0x01},
    type=t.uint8_t,
)


EtrvZb02LowBatteryValveState = enum.Enum(
    "EtrvZb02LowBatteryValveState",
    {"0%": 0, "30%": 30},
    type=t.uint8_t,
)


EtrvZb02ScheduleDay = enum.Enum(
    "EtrvZb02ScheduleDay",
    {
        "Sunday": int(SeqDayOfWeek.Sunday),
        "Monday": int(SeqDayOfWeek.Monday),
        "Tuesday": int(SeqDayOfWeek.Tuesday),
        "Wednesday": int(SeqDayOfWeek.Wednesday),
        "Thursday": int(SeqDayOfWeek.Thursday),
        "Friday": int(SeqDayOfWeek.Friday),
        "Saturday": int(SeqDayOfWeek.Saturday),
    },
    type=t.uint8_t,
)


EtrvZb02ScheduleHour = enum.Enum(
    "EtrvZb02ScheduleHour",
    {"Disabled": 0xFF, **{f"{hour:02d}": hour for hour in range(24)}},
    type=t.uint8_t,
)


EtrvZb02ScheduleMinute = enum.Enum(
    "EtrvZb02ScheduleMinute",
    {f"{minute:02d}": minute for minute in range(60)},
    type=t.uint8_t,
)


def _schedule_defaults() -> dict[int, int]:
    """Return initial local editor values."""
    values = {ETRV_ZB02_WEEKLY_SCHEDULE_DAY_ATTR: EtrvZb02ScheduleDay.Monday.value}
    for index in range(1, ETRV_ZB02_WEEKLY_SCHEDULE_MAX_PERIODS + 1):
        values[ETRV_ZB02_WEEKLY_SCHEDULE_TIME_ATTRS[index]] = (
            ETRV_ZB02_WEEKLY_SCHEDULE_NULL_TIME
        )
        values[ETRV_ZB02_WEEKLY_SCHEDULE_HOUR_ATTRS[index]] = (
            ETRV_ZB02_WEEKLY_SCHEDULE_DISABLED_HOUR
        )
        values[ETRV_ZB02_WEEKLY_SCHEDULE_MINUTE_ATTRS[index]] = 0
        values[ETRV_ZB02_WEEKLY_SCHEDULE_TEMPERATURE_ATTRS[index]] = 0
    return values


def _today_schedule_day(timezone: dt.tzinfo | None) -> int:
    """Return the local weekday using standard Thermostat day bits."""
    days = (
        EtrvZb02ScheduleDay.Monday,
        EtrvZb02ScheduleDay.Tuesday,
        EtrvZb02ScheduleDay.Wednesday,
        EtrvZb02ScheduleDay.Thursday,
        EtrvZb02ScheduleDay.Friday,
        EtrvZb02ScheduleDay.Saturday,
        EtrvZb02ScheduleDay.Sunday,
    )
    return days[dt.datetime.now(timezone).weekday()].value


def _fault_code_status(value: Any) -> str:
    """Format the documented FD22 fault bitmap."""
    fault_names = {
        0: "Internal sensor fault",
        1: "Motor operation fault",
        2: "Critical battery level",
        3: "Low battery blocks firmware upgrade",
    }
    try:
        raw_value = int(value)
    except (TypeError, ValueError):
        return "Unknown error"
    if raw_value == 0:
        return "No error"
    names = [name for bit, name in fault_names.items() if raw_value & (1 << bit)]
    unknown_bits = raw_value & ~sum(1 << bit for bit in fault_names)
    if unknown_bits:
        names.append(f"Unknown error (0x{unknown_bits:08X})")
    return ", ".join(names) or "Unknown error"


def _active_inactive(value: Any) -> str:
    """Format a zero/non-zero mode duration or flag."""
    try:
        return "Inactive" if int(value) == 0 else "Active"
    except (TypeError, ValueError):
        return "Unknown"


def _window_status(value: Any) -> str:
    """Format window-open reports."""
    try:
        return "Detected" if int(value) else "Not detected"
    except (TypeError, ValueError):
        return "Unknown"


class RtiTekEtrvZb02Thermostat(CustomCluster, Thermostat):
    """Thermostat cluster with a local 12-transition schedule editor."""

    class AttributeDefs(Thermostat.AttributeDefs):
        """Device and local editor attributes."""

        system_mode = ZCLAttributeDef(
            id=Thermostat.AttributeDefs.system_mode.id,
            type=EtrvZb02SystemMode,
            zcl_type=DataTypeId.enum8,
            access=Thermostat.AttributeDefs.system_mode.access,
        )
        weekly_schedule_day = ZCLAttributeDef(
            id=ETRV_ZB02_WEEKLY_SCHEDULE_DAY_ATTR,
            type=EtrvZb02ScheduleDay,
            access="rw",
        )
        temporary_manual_temperature = ZCLAttributeDef(
            id=ETRV_ZB02_TEMPORARY_MANUAL_TEMPERATURE_ATTR,
            type=t.int16s,
            access="rw",
        )
        for _index in range(1, ETRV_ZB02_WEEKLY_SCHEDULE_MAX_PERIODS + 1):
            locals()[f"weekly_schedule_period_{_index}_time"] = ZCLAttributeDef(
                id=ETRV_ZB02_WEEKLY_SCHEDULE_TIME_ATTRS[_index],
                type=t.uint16_t,
                access="rw",
            )
            locals()[f"weekly_schedule_period_{_index}_hour"] = ZCLAttributeDef(
                id=ETRV_ZB02_WEEKLY_SCHEDULE_HOUR_ATTRS[_index],
                type=EtrvZb02ScheduleHour,
                access="rw",
            )
            locals()[f"weekly_schedule_period_{_index}_minute"] = ZCLAttributeDef(
                id=ETRV_ZB02_WEEKLY_SCHEDULE_MINUTE_ATTRS[_index],
                type=EtrvZb02ScheduleMinute,
                access="rw",
            )
            locals()[f"weekly_schedule_period_{_index}_temperature"] = ZCLAttributeDef(
                id=ETRV_ZB02_WEEKLY_SCHEDULE_TEMPERATURE_ATTRS[_index],
                type=t.int16s,
                access="rw",
            )

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize the local-only schedule editor."""
        super().__init__(*args, **kwargs)
        self._weekly_schedule_cache: dict[int, list[tuple[int, int]]] = {}
        for attrid, value in _schedule_defaults().items():
            self._update_attribute(attrid, value)

    @staticmethod
    def _editor_attribute_ids() -> set[int]:
        return {
            ETRV_ZB02_WEEKLY_SCHEDULE_DAY_ATTR,
            *ETRV_ZB02_WEEKLY_SCHEDULE_TIME_ATTRS.values(),
            *ETRV_ZB02_WEEKLY_SCHEDULE_HOUR_ATTRS.values(),
            *ETRV_ZB02_WEEKLY_SCHEDULE_MINUTE_ATTRS.values(),
            *ETRV_ZB02_WEEKLY_SCHEDULE_TEMPERATURE_ATTRS.values(),
        }

    @staticmethod
    def _period_index(attrid: int) -> int | None:
        for attributes in (
            ETRV_ZB02_WEEKLY_SCHEDULE_TIME_ATTRS,
            ETRV_ZB02_WEEKLY_SCHEDULE_HOUR_ATTRS,
            ETRV_ZB02_WEEKLY_SCHEDULE_MINUTE_ATTRS,
            ETRV_ZB02_WEEKLY_SCHEDULE_TEMPERATURE_ATTRS,
        ):
            for index, candidate in attributes.items():
                if attrid == candidate:
                    return index
        return None

    def _editor_value(self, attrid: int) -> int:
        return int(self._attr_cache.get(attrid, _schedule_defaults()[attrid]))

    def _set_period_time(self, index: int, time: int) -> None:
        if time == ETRV_ZB02_WEEKLY_SCHEDULE_NULL_TIME:
            self._update_attribute(ETRV_ZB02_WEEKLY_SCHEDULE_TIME_ATTRS[index], time)
            self._update_attribute(
                ETRV_ZB02_WEEKLY_SCHEDULE_HOUR_ATTRS[index],
                ETRV_ZB02_WEEKLY_SCHEDULE_DISABLED_HOUR,
            )
            self._update_attribute(ETRV_ZB02_WEEKLY_SCHEDULE_MINUTE_ATTRS[index], 0)
            return
        if not 0 <= time < 24 * 60:
            raise ValueError("Weekly schedule time must be between 00:00 and 23:59")
        self._update_attribute(ETRV_ZB02_WEEKLY_SCHEDULE_TIME_ATTRS[index], time)
        self._update_attribute(ETRV_ZB02_WEEKLY_SCHEDULE_HOUR_ATTRS[index], time // 60)
        self._update_attribute(ETRV_ZB02_WEEKLY_SCHEDULE_MINUTE_ATTRS[index], time % 60)

    def _disable_period(self, index: int) -> None:
        self._set_period_time(index, ETRV_ZB02_WEEKLY_SCHEDULE_NULL_TIME)
        self._update_attribute(ETRV_ZB02_WEEKLY_SCHEDULE_TEMPERATURE_ATTRS[index], 0)

    def _periods(self) -> list[tuple[int, int]]:
        return [
            (
                self._editor_value(ETRV_ZB02_WEEKLY_SCHEDULE_TIME_ATTRS[index]),
                self._editor_value(ETRV_ZB02_WEEKLY_SCHEDULE_TEMPERATURE_ATTRS[index]),
            )
            for index in range(1, ETRV_ZB02_WEEKLY_SCHEDULE_MAX_PERIODS + 1)
        ]

    @staticmethod
    def _validate_periods(periods: list[tuple[int, int]]) -> list[tuple[int, int]]:
        transitions: list[tuple[int, int]] = []
        previous_time = -1
        for time, temperature in periods:
            if time == ETRV_ZB02_WEEKLY_SCHEDULE_NULL_TIME:
                continue
            if not 0 <= time < 24 * 60:
                raise ValueError("Weekly schedule time must be between 00:00 and 23:59")
            if time <= previous_time:
                raise ValueError("Weekly schedule periods must be strictly increasing")
            if not 500 <= temperature <= 3000:
                raise ValueError(
                    "Weekly schedule temperature must be between 5 and 30 C"
                )
            transitions.append((time, temperature))
            previous_time = time
        return transitions

    def build_weekly_schedule(
        self,
    ) -> tuple[SeqDayOfWeek, list[tuple[int, int]], list[int]]:
        """Build one standard 12-transition heating-only schedule command."""
        day = self._editor_value(ETRV_ZB02_WEEKLY_SCHEDULE_DAY_ATTR)
        if day not in {member.value for member in EtrvZb02ScheduleDay}:
            raise ValueError("Weekly schedule day must contain one weekday")
        transitions = self._validate_periods(self._periods())
        if not transitions:
            raise ValueError("Weekly schedule needs at least one period")
        device_transitions = transitions + [transitions[-1]] * (
            ETRV_ZB02_WEEKLY_SCHEDULE_MAX_PERIODS - len(transitions)
        )
        return (
            SeqDayOfWeek(day),
            device_transitions,
            [value for transition in device_transitions for value in transition],
        )

    def _load_editor(self, transitions: list[tuple[int, int]]) -> None:
        for index, (time, temperature) in enumerate(transitions, 1):
            self._set_period_time(index, time)
            self._update_attribute(
                ETRV_ZB02_WEEKLY_SCHEDULE_TEMPERATURE_ATTRS[index], temperature
            )
        for index in range(
            len(transitions) + 1, ETRV_ZB02_WEEKLY_SCHEDULE_MAX_PERIODS + 1
        ):
            self._disable_period(index)

    def _store_schedule_response(self, response: Any) -> bool:
        if isinstance(response, list | tuple):
            if len(response) == 1:
                response = response[0]
            elif len(response) == 4:
                count, day, mode, values = response
            else:
                return False
        else:
            count = day = mode = values = None
        try:
            if response is not None:
                count = response.num_transitions_for_sequence
                day = response.day_of_week_for_sequence
                mode = response.mode_for_sequence
                values = response.values
            count = int(count)
            day = int(day)
            mode = int(mode)
            values = [int(value) for value in values]
        except (AttributeError, TypeError, ValueError):
            return False
        if not 1 <= count <= ETRV_ZB02_WEEKLY_SCHEDULE_MAX_PERIODS:
            return False
        if not day or not mode & int(SeqMode.Heat) or len(values) != count * 2:
            return False
        transitions: list[tuple[int, int]] = []
        padding = False
        previous_time = -1
        for time, temperature in zip(values[::2], values[1::2], strict=True):
            if not 0 <= time < 24 * 60 or not 500 <= temperature <= 3000:
                return False
            if transitions and (time, temperature) == transitions[-1]:
                padding = True
                continue
            if padding or time <= previous_time:
                return False
            transitions.append((time, temperature))
            previous_time = time
        for member in EtrvZb02ScheduleDay:
            if day & member.value:
                self._weekly_schedule_cache[member.value] = transitions
        if day & self._editor_value(ETRV_ZB02_WEEKLY_SCHEDULE_DAY_ATTR):
            self._load_editor(transitions)
        return True

    async def schedule_fetch(
        self, expect_reply: bool = True, days_to_return: int | None = None
    ) -> Any:
        """Read one weekday via the standard Thermostat schedule command."""
        day = days_to_return or self._editor_value(ETRV_ZB02_WEEKLY_SCHEDULE_DAY_ATTR)
        response = await self.get_weekly_schedule(
            days_to_return=SeqDayOfWeek(day),
            mode_to_return=SeqMode.Heat,
            expect_reply=expect_reply,
        )
        self._store_schedule_response(response)
        return response

    async def schedule_apply(self, expect_reply: bool = False) -> Any:
        """Write and then read back one standard 12-transition schedule."""
        day, _transitions, values = self.build_weekly_schedule()
        response = await self.set_weekly_schedule(
            num_transitions_for_sequence=ETRV_ZB02_WEEKLY_SCHEDULE_MAX_PERIODS,
            day_of_week_for_sequence=day,
            mode_for_sequence=SeqMode.Heat,
            values=values,
            expect_reply=True,
        )
        if getattr(response, "status", None) != Status.SUCCESS:
            raise ValueError(
                f"Weekly schedule apply failed: {getattr(response, 'status', 'unknown')}"
            )
        await asyncio.sleep(2)
        await self.schedule_fetch(days_to_return=int(day))
        return response

    def handle_cluster_request(
        self, hdr: Any, args: Any, *args_: Any, **kwargs: Any
    ) -> Any:
        """Accept standard Get Weekly Schedule responses."""
        if hdr.command_id == 0x00 and self._store_schedule_response(args):
            return None
        return super().handle_cluster_request(hdr, args, *args_, **kwargs)

    def _update_attribute(self, attrid: int, value: Any) -> None:
        """Mirror the standard target-temperature report to its local proxy."""
        super()._update_attribute(attrid, value)
        if attrid == self.AttributeDefs.occupied_heating_setpoint.id:
            super()._update_attribute(
                ETRV_ZB02_TEMPORARY_MANUAL_TEMPERATURE_ATTR, value
            )

    async def read_attributes(
        self, attributes: list[Any], *args: Any, **kwargs: Any
    ) -> Any:
        """Prevent Zigbee reads for editor-only fields."""
        editor_attributes = []
        device_attributes = []
        for attribute in attributes:
            try:
                is_editor = (
                    self.find_attribute(attribute).id in self._editor_attribute_ids()
                )
            except KeyError:
                is_editor = False
            (editor_attributes if is_editor else device_attributes).append(attribute)
        success: dict[Any, Any] = {}
        failure: dict[Any, Any] = {}
        if editor_attributes:
            success, failure = await super().read_attributes(
                editor_attributes, *args, allow_cache=True, only_cache=True, **kwargs
            )
        if not device_attributes:
            return success, failure
        other_success, other_failure = await super().read_attributes(
            device_attributes, *args, **kwargs
        )
        return success | other_success, failure | other_failure

    async def write_attributes(
        self, attributes: dict[Any, Any], *args: Any, **kwargs: Any
    ) -> Any:
        """Edit local schedule values without sending pseudo-attributes to the device."""
        remaining = dict(attributes)
        temporary_temperature: int | None = None
        for key in list(remaining):
            try:
                attribute = self.find_attribute(key)
            except KeyError:
                continue
            if attribute.id not in self._editor_attribute_ids():
                if attribute.id == ETRV_ZB02_TEMPORARY_MANUAL_TEMPERATURE_ATTR:
                    temporary_temperature = int(remaining.pop(key))
                    if not 500 <= temporary_temperature <= 3000:
                        raise ValueError(
                            "Temporary manual temperature must be between 5 and 30 C"
                        )
                    if temporary_temperature % 50:
                        raise ValueError(
                            "Temporary manual temperature must use 0.5 C steps"
                        )
                continue
            value = int(remaining.pop(key))
            if attribute.id == ETRV_ZB02_WEEKLY_SCHEDULE_DAY_ATTR:
                if value not in {member.value for member in EtrvZb02ScheduleDay}:
                    raise ValueError("Weekly schedule day must contain one weekday")
                self._update_attribute(attribute.id, value)
                self._load_editor(self._weekly_schedule_cache.get(value, []))
                continue
            index = self._period_index(attribute.id)
            if index is None:
                continue
            time_attr = ETRV_ZB02_WEEKLY_SCHEDULE_TIME_ATTRS[index]
            hour_attr = ETRV_ZB02_WEEKLY_SCHEDULE_HOUR_ATTRS[index]
            minute_attr = ETRV_ZB02_WEEKLY_SCHEDULE_MINUTE_ATTRS[index]
            temperature_attr = ETRV_ZB02_WEEKLY_SCHEDULE_TEMPERATURE_ATTRS[index]
            periods = self._periods()
            time, temperature = periods[index - 1]
            if attribute.id == time_attr:
                time = value
            elif attribute.id == hour_attr:
                if value == ETRV_ZB02_WEEKLY_SCHEDULE_DISABLED_HOUR:
                    self._disable_period(index)
                    continue
                if not 0 <= value < 24:
                    raise ValueError("Weekly schedule hour must be 0-23")
                minute = self._editor_value(minute_attr)
                previous = next(
                    (
                        item[0]
                        for item in reversed(periods[: index - 1])
                        if item[0] != ETRV_ZB02_WEEKLY_SCHEDULE_NULL_TIME
                    ),
                    None,
                )
                if previous is not None and value == previous // 60:
                    minute = previous % 60 + 1
                if minute >= 60:
                    raise ValueError(
                        "No later weekly schedule minute is available in this hour"
                    )
                time = value * 60 + minute
            elif attribute.id == minute_attr:
                if not 0 <= value < 60:
                    raise ValueError("Weekly schedule minute must be 0-59")
                hour = self._editor_value(hour_attr)
                if hour == ETRV_ZB02_WEEKLY_SCHEDULE_DISABLED_HOUR:
                    raise ValueError("This weekly schedule period is disabled")
                time = hour * 60 + value
            else:
                if not 500 <= value <= 3000:
                    raise ValueError(
                        "Weekly schedule temperature must be between 5 and 30 C"
                    )
                temperature = value
            periods[index - 1] = (time, temperature)
            self._validate_periods(periods)
            self._set_period_time(index, time)
            self._update_attribute(temperature_attr, temperature)
        if temporary_temperature is not None:
            remaining[self.AttributeDefs.occupied_heating_setpoint.name] = (
                temporary_temperature
            )
        if remaining:
            result = await super().write_attributes(remaining, *args, **kwargs)
            if temporary_temperature is not None:
                self._update_attribute(
                    ETRV_ZB02_TEMPORARY_MANUAL_TEMPERATURE_ATTR,
                    temporary_temperature,
                )
            return result
        return {}, {}


class RtiTekEtrvZb02PrivateCluster(CustomCluster):
    """FD22 attributes and commands implemented by eTRV-ZB02."""

    cluster_id = 0xFD22
    ep_attribute = "rti_tek_etrv_zb02_private"
    report_attribute_ids: Final = frozenset(
        {
            0x0001,
            0x0002,
            0x0008,
            0x0009,
            0x000A,
            0x1000,
            0x1001,
            0x1002,
            0x1004,
            0x1005,
            0x1007,
            0x100A,
            0x1013,
            0x1017,
            0x1018,
            0x1019,
            0x101F,
        }
    )

    class ServerCommandDefs(BaseCommandDefs):
        """Commands accepted by the private cluster."""

        request_all_attributes = ZCLCommandDef(
            id=0x00, schema={}, manufacturer_code=None
        )

    class AttributeDefs(BaseAttributeDefs):
        """FD22 attribute definitions."""

        child_lock = ZCLAttributeDef(
            id=0x0001, type=t.Bool, access="rwp", manufacturer_code=None
        )
        fault_code = ZCLAttributeDef(
            id=0x0002, type=t.bitmap32, access="rp", manufacturer_code=None
        )
        product_name = ZCLAttributeDef(
            id=0x0003, type=t.CharacterString, access="r", manufacturer_code=None
        )
        screen_direction = ZCLAttributeDef(
            id=0x0008, type=t.uint8_t, access="rwp", manufacturer_code=None
        )
        screen_display_duration = ZCLAttributeDef(
            id=0x0009, type=t.uint16_t, access="rwp", manufacturer_code=None
        )
        screen_brightness = ZCLAttributeDef(
            id=0x000A, type=t.uint8_t, access="rwp", manufacturer_code=None
        )
        open_window_detection = ZCLAttributeDef(
            id=0x1000, type=t.Bool, access="rwp", manufacturer_code=None
        )
        window_state = ZCLAttributeDef(
            id=0x1001, type=t.uint8_t, access="rp", manufacturer_code=None
        )
        valve_opening = ZCLAttributeDef(
            id=0x1002, type=t.uint16_t, access="rp", manufacturer_code=None
        )
        temperature_control_mode = ZCLAttributeDef(
            id=0x1004,
            type=EtrvZb02TemperatureControlMode,
            zcl_type=DataTypeId.enum8,
            access="rwp",
            manufacturer_code=None,
        )
        valve_switching_difference = ZCLAttributeDef(
            id=0x1005, type=t.int16s, access="rwp", manufacturer_code=None
        )
        frost_protection_enabled = ZCLAttributeDef(
            id=0x1007, type=t.Bool, access="rwp", manufacturer_code=None
        )
        frost_temperature = ZCLAttributeDef(
            id=0x100A, type=t.int16s, access="rwp", manufacturer_code=None
        )
        low_battery_valve_state = ZCLAttributeDef(
            id=0x1013, type=t.uint8_t, access="rwp", manufacturer_code=None
        )
        motor_travel_calibration = ZCLAttributeDef(
            id=0x1016, type=t.Bool, access="w", manufacturer_code=None
        )
        motor_travel_calibration_status = ZCLAttributeDef(
            id=0x1017, type=t.uint8_t, access="rp", manufacturer_code=None
        )
        holiday_duration = ZCLAttributeDef(
            id=0x1018, type=t.uint32_t, access="rwp", manufacturer_code=None
        )
        boost_duration = ZCLAttributeDef(
            id=0x1019, type=t.uint32_t, access="rwp", manufacturer_code=None
        )
        temporary_manual_mode = ZCLAttributeDef(
            id=0x101F, type=t.uint8_t, access="rp", manufacturer_code=None
        )

    def reset_report_request_cycle(self) -> None:
        """Allow one full-report request in the next initialization cycle."""
        self._report_request_sent = False

    def _has_missing_report_attributes(self) -> bool:
        return any(
            self._attr_cache.get(attrid) is None for attrid in self.report_attribute_ids
        )

    async def request_reported_attributes_if_needed(self) -> bool:
        """Ask the device to report once when expected reports are absent."""
        if not self._has_missing_report_attributes():
            return False
        if getattr(self, "_report_request_sent", False):
            return True
        await self.request_all_attributes(expect_reply=False)
        self._report_request_sent = True
        return True

    async def read_attributes(
        self,
        attributes: list[Any],
        allow_cache: bool = False,
        only_cache: bool = False,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Use cache only for attributes the device reports through FD22/0x00."""
        if not allow_cache or only_cache or not attributes:
            return await super().read_attributes(
                attributes,
                *args,
                allow_cache=allow_cache,
                only_cache=only_cache,
                **kwargs,
            )
        reported, ordinary = [], []
        for attribute in attributes:
            try:
                is_reported = (
                    self.find_attribute(attribute).id in self.report_attribute_ids
                )
            except KeyError:
                is_reported = False
            (reported if is_reported else ordinary).append(attribute)
        success: dict[Any, Any] = {}
        failure: dict[Any, Any] = {}
        if reported:
            success, failure = await super().read_attributes(
                reported, *args, allow_cache=True, only_cache=True, **kwargs
            )
        if not ordinary:
            return success, failure
        other_success, other_failure = await super().read_attributes(
            ordinary,
            *args,
            allow_cache=allow_cache,
            only_cache=False,
            **kwargs,
        )
        return success | other_success, failure | other_failure

    async def write_attributes(
        self, attributes: dict[Any, Any], *args: Any, **kwargs: Any
    ) -> Any:
        """Keep Boost writes aligned to whole device minutes."""
        values = dict(attributes)
        for key in (
            self.AttributeDefs.boost_duration.name,
            self.AttributeDefs.boost_duration.id,
        ):
            if key in values:
                values[key] = max(0, int(values[key]) // 60 * 60)
        return await super().write_attributes(values, *args, **kwargs)


class RtiTekEtrvZb02Device(QuirkV2Device):
    """Request reported values and today's schedule during a live initialization."""

    async def async_initialize(self, from_cache: bool = False) -> None:
        """Synchronize device-reported values without individual FD22 reads."""
        await super().async_initialize(from_cache)
        if from_cache or not self.available:
            return
        endpoint = self.device.endpoints.get(1)
        if endpoint is None:
            return
        private = endpoint.in_clusters.get(RtiTekEtrvZb02PrivateCluster.cluster_id)
        if isinstance(private, RtiTekEtrvZb02PrivateCluster):
            private.reset_report_request_cycle()
            try:
                await private.request_reported_attributes_if_needed()
            except Exception:  # noqa: BLE001
                self.debug("eTRV-ZB02 full report request failed", exc_info=True)
        thermostat = endpoint.in_clusters.get(Thermostat.cluster_id)
        if isinstance(thermostat, RtiTekEtrvZb02Thermostat):
            day = _today_schedule_day(self.gateway.config.local_timezone)
            thermostat._update_attribute(ETRV_ZB02_WEEKLY_SCHEDULE_DAY_ATTR, day)
            try:
                await thermostat.schedule_fetch(days_to_return=day)
            except Exception:  # noqa: BLE001
                self.debug("eTRV-ZB02 daily schedule request failed", exc_info=True)


ETRV_ZB02_QUIRK = (
    QuirkBuilder("Rti-Tek", "eTRV-ZB02")
    .zha_device_class(RtiTekEtrvZb02Device)
    .replaces(RtiTekEtrvZb02Thermostat)
    .replaces(RtiTekEtrvZb02PrivateCluster)
    .prevent_default_entity_creation(cluster_id=Identify.cluster_id)
    .number(
        Thermostat.AttributeDefs.local_temperature_calibration.name,
        Thermostat.cluster_id,
        min_value=-10,
        max_value=10,
        step=0.1,
        multiplier=0.1,
        unit=UnitOfTemperature.CELSIUS,
        mode="slider",
        entity_type=EntityType.CONFIG,
        unique_id_suffix="temperature_offset",
        translation_key="temperature_offset",
        fallback_name="Temperature offset",
    )
    .sensor(
        Basic.AttributeDefs.manufacturer_version_details.name,
        Basic.cluster_id,
        attribute_initialized_from_cache=False,
        translation_key="version",
        fallback_name="Version",
    )
    .switch(
        RtiTekEtrvZb02PrivateCluster.AttributeDefs.child_lock.name,
        RtiTekEtrvZb02PrivateCluster.cluster_id,
        attribute_initialized_from_cache=True,
        translation_key="child_lock",
        fallback_name="Child lock",
    )
    .switch(
        RtiTekEtrvZb02PrivateCluster.AttributeDefs.open_window_detection.name,
        RtiTekEtrvZb02PrivateCluster.cluster_id,
        attribute_initialized_from_cache=True,
        translation_key="open_window_detection",
        fallback_name="Open window detection",
    )
    .switch(
        RtiTekEtrvZb02PrivateCluster.AttributeDefs.frost_protection_enabled.name,
        RtiTekEtrvZb02PrivateCluster.cluster_id,
        attribute_initialized_from_cache=True,
        translation_key="frost_protection_enabled",
        fallback_name="Frost protection",
    )
    .number(
        RtiTekEtrvZb02PrivateCluster.AttributeDefs.frost_temperature.name,
        RtiTekEtrvZb02PrivateCluster.cluster_id,
        min_value=5,
        max_value=9,
        step=0.5,
        multiplier=0.01,
        device_class=NumberDeviceClass.TEMPERATURE,
        unit=UnitOfTemperature.CELSIUS,
        entity_type=EntityType.CONFIG,
        translation_key="frost_temperature",
        fallback_name="Frost temperature",
    )
    .enum(
        RtiTekEtrvZb02PrivateCluster.AttributeDefs.temperature_control_mode.name,
        EtrvZb02TemperatureControlMode,
        RtiTekEtrvZb02PrivateCluster.cluster_id,
        attribute_initialized_from_cache=True,
        translation_key="temperature_control_mode",
        fallback_name="Temperature control mode",
    )
    .enum(
        RtiTekEtrvZb02PrivateCluster.AttributeDefs.screen_brightness.name,
        EtrvZb02ScreenBrightness,
        RtiTekEtrvZb02PrivateCluster.cluster_id,
        attribute_initialized_from_cache=True,
        translation_key="screen_brightness",
        fallback_name="Screen brightness",
    )
    .enum(
        RtiTekEtrvZb02PrivateCluster.AttributeDefs.screen_direction.name,
        EtrvZb02ScreenDirection,
        RtiTekEtrvZb02PrivateCluster.cluster_id,
        attribute_initialized_from_cache=True,
        translation_key="screen_direction",
        fallback_name="Screen direction",
    )
    .enum(
        RtiTekEtrvZb02PrivateCluster.AttributeDefs.screen_display_duration.name,
        EtrvZb02ScreenDisplayDuration,
        RtiTekEtrvZb02PrivateCluster.cluster_id,
        attribute_initialized_from_cache=True,
        translation_key="screen_display_duration",
        fallback_name="Screen display duration",
    )
    .number(
        RtiTekEtrvZb02PrivateCluster.AttributeDefs.boost_duration.name,
        RtiTekEtrvZb02PrivateCluster.cluster_id,
        min_value=0,
        max_value=180,
        step=1,
        multiplier=1 / 60,
        device_class=NumberDeviceClass.DURATION,
        unit=UnitOfTime.MINUTES,
        mode="slider",
        entity_type=EntityType.CONFIG,
        translation_key="boost_duration",
        fallback_name="Boost duration",
    )
    .enum(
        RtiTekEtrvZb02PrivateCluster.AttributeDefs.low_battery_valve_state.name,
        EtrvZb02LowBatteryValveState,
        RtiTekEtrvZb02PrivateCluster.cluster_id,
        attribute_initialized_from_cache=True,
        translation_key="low_battery_valve_state",
        fallback_name="Low battery valve state",
    )
    .sensor(
        RtiTekEtrvZb02PrivateCluster.AttributeDefs.window_state.name,
        RtiTekEtrvZb02PrivateCluster.cluster_id,
        attribute_initialized_from_cache=True,
        attribute_converter=_window_status,
        translation_key="open_window_detected",
        fallback_name="Open window detected",
    )
    .sensor(
        RtiTekEtrvZb02PrivateCluster.AttributeDefs.valve_opening.name,
        RtiTekEtrvZb02PrivateCluster.cluster_id,
        divisor=10,
        unit="%",
        translation_key="valve_opening",
        fallback_name="Valve opening",
    )
    .sensor(
        RtiTekEtrvZb02PrivateCluster.AttributeDefs.fault_code.name,
        RtiTekEtrvZb02PrivateCluster.cluster_id,
        attribute_initialized_from_cache=True,
        attribute_converter=_fault_code_status,
        translation_key="fault_code",
        fallback_name="Fault code",
    )
    .sensor(
        RtiTekEtrvZb02PrivateCluster.AttributeDefs.motor_travel_calibration_status.name,
        RtiTekEtrvZb02PrivateCluster.cluster_id,
        attribute_initialized_from_cache=True,
        attribute_converter=lambda value: "Success" if int(value) == 0 else "Failed",
        translation_key="motor_travel_calibration_status",
        fallback_name="Valve calibration status",
    )
    .sensor(
        RtiTekEtrvZb02PrivateCluster.AttributeDefs.product_name.name,
        RtiTekEtrvZb02PrivateCluster.cluster_id,
        attribute_initialized_from_cache=False,
        translation_key="product_name",
        fallback_name="Product name",
    )
    .sensor(
        RtiTekEtrvZb02PrivateCluster.AttributeDefs.temporary_manual_mode.name,
        RtiTekEtrvZb02PrivateCluster.cluster_id,
        attribute_initialized_from_cache=True,
        attribute_converter=_active_inactive,
        translation_key="temporary_manual_mode",
        fallback_name="Temporary manual mode",
    )
    .number(
        RtiTekEtrvZb02PrivateCluster.AttributeDefs.valve_switching_difference.name,
        RtiTekEtrvZb02PrivateCluster.cluster_id,
        min_value=0.5,
        max_value=5,
        step=0.1,
        multiplier=0.01,
        device_class=NumberDeviceClass.TEMPERATURE_DELTA,
        unit=UnitOfTemperature.CELSIUS,
        entity_type=EntityType.CONFIG,
        translation_key="valve_switching_difference",
        fallback_name="Valve switching difference",
    )
    .sensor(
        RtiTekEtrvZb02PrivateCluster.AttributeDefs.holiday_duration.name,
        RtiTekEtrvZb02PrivateCluster.cluster_id,
        attribute_initialized_from_cache=True,
        attribute_converter=_active_inactive,
        translation_key="holiday_mode",
        fallback_name="Holiday mode",
    )
    .enum(
        RtiTekEtrvZb02Thermostat.AttributeDefs.system_mode.name,
        EtrvZb02SystemMode,
        Thermostat.cluster_id,
        translation_key="system_mode",
        fallback_name="System mode",
    )
    .number(
        RtiTekEtrvZb02Thermostat.AttributeDefs.temporary_manual_temperature.name,
        Thermostat.cluster_id,
        min_value=5,
        max_value=30,
        step=0.5,
        multiplier=0.01,
        device_class=NumberDeviceClass.TEMPERATURE,
        unit=UnitOfTemperature.CELSIUS,
        mode="slider",
        entity_type=EntityType.CONFIG,
        translation_key="temporary_manual_temperature",
        fallback_name="Temporary manual temperature",
    )
    .write_attr_button(
        attribute_name=RtiTekEtrvZb02PrivateCluster.AttributeDefs.motor_travel_calibration.name,
        cluster_id=RtiTekEtrvZb02PrivateCluster.cluster_id,
        attribute_value=0x01,
        unique_id_suffix="start_motor_travel_calibration",
        translation_key="calibrate_valve",
        fallback_name="Calibrate valve",
    )
    .command_button(
        "schedule_apply",
        Thermostat.cluster_id,
        unique_id_suffix="weekly_schedule_apply",
        translation_key="weekly_schedule_apply",
        fallback_name="Weekly schedule apply",
    )
    .command_button(
        "schedule_fetch",
        Thermostat.cluster_id,
        unique_id_suffix="weekly_schedule_fetch",
        translation_key="weekly_schedule_fetch",
        fallback_name="Weekly schedule fetch",
    )
    .enum(
        RtiTekEtrvZb02Thermostat.AttributeDefs.weekly_schedule_day.name,
        EtrvZb02ScheduleDay,
        Thermostat.cluster_id,
        attribute_initialized_from_cache=True,
        translation_key="weekly_schedule_day",
        fallback_name="Weekly schedule day",
    )
)

for _index in range(1, ETRV_ZB02_WEEKLY_SCHEDULE_MAX_PERIODS + 1):
    ETRV_ZB02_QUIRK = (
        ETRV_ZB02_QUIRK.enum(
            getattr(
                RtiTekEtrvZb02Thermostat.AttributeDefs,
                f"weekly_schedule_period_{_index}_hour",
            ).name,
            EtrvZb02ScheduleHour,
            Thermostat.cluster_id,
            attribute_initialized_from_cache=True,
            translation_key=f"weekly_schedule_period_{_index}_hour",
            fallback_name=f"Weekly schedule period {_index} hour",
        )
        .enum(
            getattr(
                RtiTekEtrvZb02Thermostat.AttributeDefs,
                f"weekly_schedule_period_{_index}_minute",
            ).name,
            EtrvZb02ScheduleMinute,
            Thermostat.cluster_id,
            attribute_initialized_from_cache=True,
            translation_key=f"weekly_schedule_period_{_index}_minute",
            fallback_name=f"Weekly schedule period {_index} minute",
        )
        .number(
            getattr(
                RtiTekEtrvZb02Thermostat.AttributeDefs,
                f"weekly_schedule_period_{_index}_temperature",
            ).name,
            Thermostat.cluster_id,
            min_value=5,
            max_value=30,
            step=0.5,
            multiplier=0.01,
            device_class=NumberDeviceClass.TEMPERATURE,
            unit=UnitOfTemperature.CELSIUS,
            entity_type=EntityType.CONFIG,
            translation_key=f"weekly_schedule_period_{_index}_temperature",
            fallback_name=f"Weekly schedule period {_index} temperature",
        )
    )

ETRV_ZB02_QUIRK.add_to_registry()
