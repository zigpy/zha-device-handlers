"""Sonoff TRVZB - Zigbee Thermostatic Radiator Valve."""

import asyncio
from datetime import datetime
import logging

import zigpy.types as t
from zigpy.zcl.clusters.general import Basic
from zigpy.zcl.clusters.hvac import Thermostat
from zigpy.zcl.foundation import (
    BaseAttributeDefs,
    BaseCommandDefs,
    DataTypeId,
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
from zhaquirks.clusters import CustomCluster

LOGGER = logging.getLogger(__name__)

SONOFF_TRVZBT_PRIVATE_CLUSTER_ID = 0xFC11
SONOFF_TRVZBT_TEMPORARY_MODE_ATTR = 0x6014


class SonoffScreenDirection(t.enum8):
    """Screen direction."""

    Degree_0 = 0x00
    Degree_90 = 0x01
    Degree_180 = 0x02
    Degree_270 = 0x03


class SonoffLowBatteryValveState(t.enum8):
    """Valve state used when the battery is too low."""

    Close = 0x00
    Open_30 = 0x1E


class SonoffTemperatureSensorSelect(t.enum8):
    """Temperature sensor source."""

    Internal = 0x00
    External = 0x01
    External_2 = 0x02
    External_3 = 0x03


class SonoffTemporaryMode(t.enum8):
    """Temporary mode."""

    Boost = 0x00
    Timer = 0x01
    None_ = 0xFF


class SonoffTemporaryModeEditor(t.enum8):
    """Local editor values for temporary mode; avoids 0 as a selectable value."""

    None_ = 0x03
    Boost = 0x01
    Timer = 0x02


class SonoffSystemMode(t.enum8):
    """Thermostat system modes exposed by Zigbee2MQTT for TRV-ZBT."""

    Off = 0x00
    Auto = 0x01
    Manual = 0x04


class SonoffDeviceWorkMode(t.enum8):
    """Device work mode reported by the private cluster."""

    Single_Fire = 0x00
    Zero_Fire = 0x01
    Frost_Protection = 0x02
    Manual = 0x03
    Schedule = 0x04
    Temporary_Manual = 0x05


SONOFF_TRVZBT_DEVICE_WORK_MODE_LOOKUP = {
    0x00: "Single Fire",
    0x01: "Zero Fire",
    0x02: "Frost Protection",
    0x03: "Manual",
    0x04: "Schedule",
    0x05: "Temporary Manual",
}


class SonoffMotorTravelCalibrationStatus(t.enum8):
    """Motor travel calibration result."""

    Failed = 0x01


class SonoffScheduleGroup(t.enum8):
    """Editable weekly schedule group."""

    Schedule_1 = 0x00
    Schedule_2 = 0x01
    Schedule_3 = 0x02


class SonoffScheduleDay(t.enum8):
    """Editable weekly schedule operating day bitmask."""

    Sunday = 0x01
    Monday = 0x02
    Tuesday = 0x04
    Wednesday = 0x08
    Thursday = 0x10
    Friday = 0x20
    Saturday = 0x40


class SonoffScheduleTime(t.enum16):
    """Editable schedule transition time in minutes after midnight."""

    NULL = 0xFFFF
    locals()["00:00"] = 0
    locals()["00:30"] = 30
    locals()["01:00"] = 60
    locals()["01:30"] = 90
    locals()["02:00"] = 120
    locals()["02:30"] = 150
    locals()["03:00"] = 180
    locals()["03:30"] = 210
    locals()["04:00"] = 240
    locals()["04:30"] = 270
    locals()["05:00"] = 300
    locals()["05:30"] = 330
    locals()["06:00"] = 360
    locals()["06:30"] = 390
    locals()["07:00"] = 420
    locals()["07:30"] = 450
    locals()["08:00"] = 480
    locals()["08:30"] = 510
    locals()["09:00"] = 540
    locals()["09:30"] = 570
    locals()["10:00"] = 600
    locals()["10:30"] = 630
    locals()["11:00"] = 660
    locals()["11:30"] = 690
    locals()["12:00"] = 720
    locals()["12:30"] = 750
    locals()["13:00"] = 780
    locals()["13:30"] = 810
    locals()["14:00"] = 840
    locals()["14:30"] = 870
    locals()["15:00"] = 900
    locals()["15:30"] = 930
    locals()["16:00"] = 960
    locals()["16:30"] = 990
    locals()["17:00"] = 1020
    locals()["17:30"] = 1050
    locals()["18:00"] = 1080
    locals()["18:30"] = 1110
    locals()["19:00"] = 1140
    locals()["19:30"] = 1170
    locals()["20:00"] = 1200
    locals()["20:30"] = 1230
    locals()["21:00"] = 1260
    locals()["21:30"] = 1290
    locals()["22:00"] = 1320
    locals()["22:30"] = 1350
    locals()["23:00"] = 1380
    locals()["23:30"] = 1410


SONOFF_TRVZBT_FAULT_CODE_LOOKUP = {
    0: "Temperature sensor issue",
    1: "Valve adjustment issue",
    2: "Low battery",
    3: "Low battery for firmware upgrade",
    4: "Battery status abnormal",
    5: "External temperature sensor issue",
}
SONOFF_TRVZBT_KNOWN_FAULT_CODE_MASK = sum(
    1 << bit for bit in SONOFF_TRVZBT_FAULT_CODE_LOOKUP
)
SONOFF_TRVZBT_MOTOR_TRAVEL_CALIBRATION_STATUS_LOOKUP = {
    0x00: "Normal",
    0x01: "Failed",
}

SONOFF_TRVZBT_SCHEDULE_DAY_LOOKUP = {
    0x01: "Sunday",
    0x02: "Monday",
    0x04: "Tuesday",
    0x08: "Wednesday",
    0x10: "Thursday",
    0x20: "Friday",
    0x40: "Saturday",
}
SONOFF_TRVZBT_SCHEDULE_DAY_BITS = tuple(SONOFF_TRVZBT_SCHEDULE_DAY_LOOKUP)
SONOFF_TRVZBT_SCHEDULE_GROUP_VALUES = tuple(
    int(group)
    for group in (
        SonoffScheduleGroup.Schedule_1,
        SonoffScheduleGroup.Schedule_2,
        SonoffScheduleGroup.Schedule_3,
    )
)

SONOFF_TRVZBT_WEEKLY_PROGRAM_STATE_DAY_LOOKUP = {
    0x01: "Monday",
    0x02: "Tuesday",
    0x04: "Wednesday",
    0x08: "Thursday",
    0x10: "Friday",
    0x20: "Saturday",
    0x40: "Sunday",
}
SONOFF_TRVZBT_ISO_WEEKDAY_TO_SCHEDULE_DAY = {
    1: int(SonoffScheduleDay.Monday),
    2: int(SonoffScheduleDay.Tuesday),
    3: int(SonoffScheduleDay.Wednesday),
    4: int(SonoffScheduleDay.Thursday),
    5: int(SonoffScheduleDay.Friday),
    6: int(SonoffScheduleDay.Saturday),
    7: int(SonoffScheduleDay.Sunday),
}


def _sonoff_trvzbt_today_schedule_day():
    """Return today's schedule day bit using the HA host local date."""

    return SONOFF_TRVZBT_ISO_WEEKDAY_TO_SCHEDULE_DAY.get(
        datetime.now().isoweekday(), int(SonoffScheduleDay.Sunday)
    )


SONOFF_TRVZBT_SCHEDULE_ATTR_BY_DAY = {
    0x01: 0xF001,
    0x02: 0xF002,
    0x04: 0xF003,
    0x08: 0xF004,
    0x10: 0xF005,
    0x20: 0xF006,
    0x40: 0xF007,
}
SONOFF_TRVZBT_SCHEDULE_STATUS_ATTR = 0xF008
SONOFF_TRVZBT_BLUETOOTH_PAIRING_STATUS_ATTR = 0xF009
SONOFF_TRVZBT_BLUETOOTH_PAIRING_REQUEST_ATTR = 0xF00A
SONOFF_TRVZBT_LOCAL_TEMPERATURE_OFFSET_ATTR = 0xF00B
SONOFF_TRVZBT_SCHEDULE_EDITOR_GROUP_ATTR = 0xF010
SONOFF_TRVZBT_SCHEDULE_EDITOR_DAY_ATTR = 0xF011
SONOFF_TRVZBT_SCHEDULE_EDITOR_PERIOD_COUNT_ATTR = 0xF012
SONOFF_TRVZBT_SCHEDULE_EDITOR_APPLY_STATUS_ATTR = 0xF013
SONOFF_TRVZBT_TEMPORARY_MODE_EDITOR_MODE_ATTR = 0xF014
SONOFF_TRVZBT_TEMPORARY_MODE_EDITOR_DURATION_ATTR = 0xF015
SONOFF_TRVZBT_TEMPORARY_MODE_EDITOR_TARGET_TEMPERATURE_ATTR = 0xF016
SONOFF_TRVZBT_TEMPORARY_MODE_EDITOR_APPLY_STATUS_ATTR = 0xF017
SONOFF_TRVZBT_SCHEDULE_EDITOR_MAX_PERIODS = 12
SONOFF_TRVZBT_SCHEDULE_EDITOR_NULL_TIME = int(SonoffScheduleTime.NULL)
SONOFF_TRVZBT_SCHEDULE_EDITOR_PERIOD_TIME_ATTRS = {
    index: 0xF020 + index - 1
    for index in range(1, SONOFF_TRVZBT_SCHEDULE_EDITOR_MAX_PERIODS + 1)
}
SONOFF_TRVZBT_SCHEDULE_EDITOR_PERIOD_TEMP_ATTRS = {
    index: 0xF030 + index - 1
    for index in range(1, SONOFF_TRVZBT_SCHEDULE_EDITOR_MAX_PERIODS + 1)
}

SONOFF_TRVZBT_SCHEDULE_EDITOR_DEFAULTS = {
    SONOFF_TRVZBT_SCHEDULE_EDITOR_GROUP_ATTR: 0,
    SONOFF_TRVZBT_SCHEDULE_EDITOR_PERIOD_COUNT_ATTR: SONOFF_TRVZBT_SCHEDULE_EDITOR_MAX_PERIODS,
    SONOFF_TRVZBT_SCHEDULE_EDITOR_APPLY_STATUS_ATTR: "not applied",
    SONOFF_TRVZBT_TEMPORARY_MODE_EDITOR_MODE_ATTR: int(SonoffTemporaryModeEditor.Timer),
    SONOFF_TRVZBT_TEMPORARY_MODE_EDITOR_DURATION_ATTR: 60 * 60,
    SONOFF_TRVZBT_TEMPORARY_MODE_EDITOR_TARGET_TEMPERATURE_ATTR: 2100,
    SONOFF_TRVZBT_TEMPORARY_MODE_EDITOR_APPLY_STATUS_ATTR: "not applied",
    SONOFF_TRVZBT_SCHEDULE_EDITOR_PERIOD_TEMP_ATTRS[1]: 1600,
    SONOFF_TRVZBT_SCHEDULE_EDITOR_PERIOD_TEMP_ATTRS[2]: 1900,
    SONOFF_TRVZBT_SCHEDULE_EDITOR_PERIOD_TEMP_ATTRS[3]: 1600,
    SONOFF_TRVZBT_SCHEDULE_EDITOR_PERIOD_TEMP_ATTRS[4]: 1900,
    SONOFF_TRVZBT_SCHEDULE_EDITOR_PERIOD_TEMP_ATTRS[5]: 1600,
    SONOFF_TRVZBT_SCHEDULE_EDITOR_PERIOD_TEMP_ATTRS[6]: 1600,
    SONOFF_TRVZBT_SCHEDULE_EDITOR_PERIOD_TEMP_ATTRS[7]: 1600,
    SONOFF_TRVZBT_SCHEDULE_EDITOR_PERIOD_TEMP_ATTRS[8]: 1600,
    SONOFF_TRVZBT_SCHEDULE_EDITOR_PERIOD_TEMP_ATTRS[9]: 1600,
    SONOFF_TRVZBT_SCHEDULE_EDITOR_PERIOD_TEMP_ATTRS[10]: 1600,
    SONOFF_TRVZBT_SCHEDULE_EDITOR_PERIOD_TEMP_ATTRS[11]: 1600,
    SONOFF_TRVZBT_SCHEDULE_EDITOR_PERIOD_TEMP_ATTRS[12]: 1600,
}
for index in range(1, SONOFF_TRVZBT_SCHEDULE_EDITOR_MAX_PERIODS + 1):
    SONOFF_TRVZBT_SCHEDULE_EDITOR_DEFAULTS[
        SONOFF_TRVZBT_SCHEDULE_EDITOR_PERIOD_TIME_ATTRS[index]
    ] = (index - 1) * 120

SONOFF_TRVZBT_DEFAULT_SCHEDULE_TRANSITIONS = tuple(
    (
        SONOFF_TRVZBT_SCHEDULE_EDITOR_DEFAULTS[
            SONOFF_TRVZBT_SCHEDULE_EDITOR_PERIOD_TIME_ATTRS[index]
        ],
        SONOFF_TRVZBT_SCHEDULE_EDITOR_DEFAULTS[
            SONOFF_TRVZBT_SCHEDULE_EDITOR_PERIOD_TEMP_ATTRS[index]
        ],
    )
    for index in range(1, SONOFF_TRVZBT_SCHEDULE_EDITOR_MAX_PERIODS + 1)
)


SONOFF_TRVZBT_BLUETOOTH_PAIRING_REQUEST_BY_EVENT = {
    0x01: True,
    0x02: False,
}


class SonoffScheduleGroupCommand:
    """Private TRV-ZBT schedule command with read/write payload variants."""

    def __init__(
        self,
        schedule_type,
        read_or_write,
        active_num,
        transition_count=None,
        day_of_week=None,
        mode=None,
        **kwargs,
    ):
        """Initialize a schedule command from its variable payload fields."""
        self.schedule_type = int(schedule_type)
        self.read_or_write = int(read_or_write)
        self.active_num = int(active_num)

        self.transition_count = (
            None if transition_count is None else int(transition_count)
        )
        self.day_of_week = None if day_of_week is None else int(day_of_week)
        self.mode = None if mode is None else int(mode)

        self.transitions = kwargs

    def serialize(self):
        """Serialize read as 3 bytes and write as a variable schedule payload."""

        payload = bytes(
            (
                self._uint8(self.schedule_type, "schedule_type"),
                self._uint8(self.read_or_write, "read_or_write"),
                self._uint8(self.active_num, "active_num"),
            )
        )

        if self.read_or_write == 0x00:
            return payload

        if self.read_or_write != 0x01:
            raise ValueError(
                f"Unsupported schedule read_or_write: {self.read_or_write}"
            )

        transition_count = self._required("transition_count", self.transition_count)
        day_of_week = self._required("day_of_week", self.day_of_week)
        mode = self._required("mode", self.mode)

        payload += bytes(
            (
                self._uint8(transition_count, "transition_count"),
                self._uint8(day_of_week, "day_of_week"),
                self._uint8(mode, "mode"),
            )
        )

        for index in range(1, transition_count + 1):
            transition_time = self._required(
                f"transition_{index}_time",
                self.transitions.get(f"transition_{index}_time"),
            )
            heat_setpoint = self._required(
                f"transition_{index}_heat_setpoint",
                self.transitions.get(f"transition_{index}_heat_setpoint"),
            )
            payload += self._uint16_le(transition_time, f"transition_{index}_time")
            payload += self._int16_le(
                heat_setpoint, f"transition_{index}_heat_setpoint"
            )

        return payload

    def __repr__(self):
        """Return a debug representation of the command payload."""
        fields = [
            f"schedule_type={self.schedule_type}",
            f"read_or_write={self.read_or_write}",
            f"active_num={self.active_num}",
        ]
        if self.transition_count is not None:
            fields.extend(
                [
                    f"transition_count={self.transition_count}",
                    f"day_of_week={self.day_of_week}",
                    f"mode={self.mode}",
                ]
            )
            for index in range(1, self.transition_count + 1):
                fields.append(
                    f"transition_{index}_time="
                    f"{self.transitions.get(f'transition_{index}_time')}"
                )
                fields.append(
                    f"transition_{index}_heat_setpoint="
                    f"{self.transitions.get(f'transition_{index}_heat_setpoint')}"
                )
        return f"{type(self).__name__}({', '.join(fields)})"

    @staticmethod
    def _required(name, value):
        if value is None:
            raise ValueError(f"Value for field {name!r} is required")
        return int(value)

    @staticmethod
    def _uint8(value, name):
        value = int(value)
        if value < 0 or value > 0xFF:
            raise ValueError(f"{name} must be uint8")
        return value

    @staticmethod
    def _uint16_le(value, name):
        value = int(value)
        if value < 0 or value > 0xFFFF:
            raise ValueError(f"{name} must be uint16")
        return value.to_bytes(2, "little")

    @staticmethod
    def _int16_le(value, name):
        value = int(value)
        if value < -0x8000 or value > 0x7FFF:
            raise ValueError(f"{name} must be int16")
        return value.to_bytes(2, "little", signed=True)


class SonoffRawBytes(bytes):
    """Raw command payload without a length prefix."""

    def serialize(self):
        """Serialize bytes as-is."""

        return bytes(self)

    @classmethod
    def deserialize(cls, data):
        """Consume the remaining bytes as one field."""

        return cls(data), b""


class SonoffHvacMessageNotification(bytes):
    """Normalize the 0x6030 ZCL array report into bytes."""

    def __new__(cls, value=b""):
        """Accept zigpy Array objects, lists, tuples, and raw bytes."""

        if value is None:
            data = b""
        elif isinstance(value, (bytes, bytearray)):
            data = bytes(value)
        else:
            array_value = getattr(value, "value", None)
            if array_value is None:
                array_value = getattr(value, "values", None)

            if array_value is not None:
                data = bytes(int(item) for item in array_value)
            else:
                try:
                    data = bytes(int(item) for item in value)
                except TypeError:
                    data = b""

        return super().__new__(cls, data)

    def serialize(self):
        """Serialize bytes as-is."""

        return bytes(self)

    @classmethod
    def deserialize(cls, data):
        """Consume the remaining bytes as one field."""

        return cls(data), b""


def convert_sonoff_trvzbt_fault_code(value):
    """Decode the TRV-ZBT packed fault code."""

    try:
        raw_value = int(value)
    except (TypeError, ValueError):
        return "Unknown"

    if raw_value < 0 or raw_value > 0xFFFFFFFF:
        return "Unknown"

    if raw_value == 0:
        return "Normal"

    feature = (raw_value >> 24) & 0xFF
    length = (raw_value >> 16) & 0xFF
    fault_bits = raw_value & 0xFFFF
    if feature == 0x0A and length in (1, 2):
        raw_value = fault_bits

    descriptions = [
        description
        for bit, description in SONOFF_TRVZBT_FAULT_CODE_LOOKUP.items()
        if raw_value & (1 << bit)
    ]

    if not descriptions:
        return "Normal" if raw_value == 0 else "Unknown"

    if raw_value & ~SONOFF_TRVZBT_KNOWN_FAULT_CODE_MASK:
        descriptions.append("Unknown")

    return ", ".join(descriptions)


def convert_sonoff_trvzbt_motor_travel_calibration_status(value):
    """Decode the TRV-ZBT motor travel calibration status."""

    try:
        raw_value = int(value)
    except (TypeError, ValueError):
        return "Unknown"

    return SONOFF_TRVZBT_MOTOR_TRAVEL_CALIBRATION_STATUS_LOOKUP.get(
        raw_value, f"Unknown 0x{raw_value:02X}"
    )


def convert_sonoff_trvzbt_device_work_mode(value):
    """Decode the TRV-ZBT device work mode."""

    try:
        raw_value = int(getattr(value, "value", value))
    except (TypeError, ValueError):
        return "Unknown"

    return SONOFF_TRVZBT_DEVICE_WORK_MODE_LOOKUP.get(
        raw_value, f"Unknown 0x{raw_value:02X}"
    )


def convert_sonoff_trvzbt_open_window_detected(value):
    """Decode the TRV-ZBT HVAC notification payload."""

    if value is None:
        return None

    try:
        data = bytes(value)
    except TypeError:
        try:
            data = bytes(int(item) for item in value)
        except (TypeError, ValueError):
            return None

    if not data:
        return "Not detected"

    if len(data) >= 6 and data[0] == 0x20:
        element_count = int.from_bytes(data[1:3], "little")
        if element_count <= len(data) - 3:
            data = data[3 : 3 + element_count]

    if len(data) < 3 or data[0] != 0x00 or data[1] < 1:
        return None

    return "Detected" if data[2] == 0x01 else "Not detected"


def convert_sonoff_trvzbt_weekly_program_state(value):
    """Decode the weekly program enabled-day bitmap."""

    try:
        raw_value = int(value)
    except (TypeError, ValueError):
        return "unknown"

    days = [
        day_name
        for day_bit, day_name in SONOFF_TRVZBT_WEEKLY_PROGRAM_STATE_DAY_LOOKUP.items()
        if raw_value & day_bit
    ]
    if not days:
        return "none"

    if raw_value & ~0x7F:
        days.append("unknown")

    return ", ".join(days)


def _sonoff_trvzbt_bytes(value):
    """Return command payload bytes from zigpy decoded arguments."""

    if isinstance(value, (bytes, bytearray)):
        return bytes(value)

    if isinstance(value, (list, tuple)) and len(value) == 1:
        return _sonoff_trvzbt_bytes(value[0])

    try:
        return bytes(value)
    except TypeError:
        return b""


def parse_sonoff_trvzbt_schedule_group(value):
    """Decode a TRV-ZBT private schedule group response."""

    data = _sonoff_trvzbt_bytes(value)
    if len(data) == 4 and data[1] == 0x01:
        return {
            "response_type": "write",
            "schedule_type": data[0],
            "read_or_write": data[1],
            "active_num": data[2],
            "status": data[3],
            "status_name": "success" if data[3] == 0x00 else "fail",
            "raw": data.hex(" "),
        }

    if len(data) < 6:
        return None

    schedule_type = data[0]
    read_or_write = data[1]
    active_num = data[2]
    transition_count = data[3]
    day_of_week = data[4]
    mode = data[5]

    transitions = []
    offset = 6
    for _ in range(transition_count):
        if offset + 4 > len(data):
            break

        minutes = int.from_bytes(data[offset : offset + 2], "little")
        heat_setpoint = int.from_bytes(
            data[offset + 2 : offset + 4], "little", signed=True
        )
        offset += 4

        if minutes > 24 * 60:
            continue

        transitions.append((minutes, heat_setpoint / 100))

    if not transitions:
        return None

    deduped_transitions = []
    for transition in transitions:
        if transition not in deduped_transitions:
            deduped_transitions.append(transition)

    schedule = " ".join(
        f"{minutes // 60:02d}:{minutes % 60:02d}/{temperature:g}"
        for minutes, temperature in deduped_transitions
    )
    editor_transitions = [
        (minutes, round(temperature * 100))
        for minutes, temperature in transitions[
            :SONOFF_TRVZBT_SCHEDULE_EDITOR_MAX_PERIODS
        ]
    ]
    day_names = [
        SONOFF_TRVZBT_SCHEDULE_DAY_LOOKUP[day_bit]
        for day_bit in SONOFF_TRVZBT_SCHEDULE_DAY_BITS
        if day_of_week & day_bit
    ]

    return {
        "response_type": "read",
        "schedule_type": schedule_type,
        "read_or_write": read_or_write,
        "active_num": active_num,
        "transition_count": transition_count,
        "day_of_week": day_of_week,
        "day_name": ", ".join(day_names)
        if day_names
        else f"unknown_0x{day_of_week:02x}",
        "mode": mode,
        "schedule": schedule,
        "editor_transitions": editor_transitions,
        "raw": data.hex(" "),
    }


def _sonoff_trvzbt_uint8(value, name):
    value = int(value)
    if value < 0 or value > 0xFF:
        raise ValueError(f"{name} must be uint8")
    return value


def _sonoff_trvzbt_uint16(value, name):
    value = int(value)
    if value < 0 or value > 0xFFFF:
        raise ValueError(f"{name} must be uint16")
    return value


def _sonoff_trvzbt_int16(value, name):
    value = int(value)
    if value < -0x8000 or value > 0x7FFF:
        raise ValueError(f"{name} must be int16")
    return value


def _sonoff_trvzbt_get_attr(cluster, attrid):
    value = cluster._attr_cache.get(
        attrid, SONOFF_TRVZBT_SCHEDULE_EDITOR_DEFAULTS.get(attrid)
    )
    if attrid == SONOFF_TRVZBT_SCHEDULE_EDITOR_DAY_ATTR:
        default_day = _sonoff_trvzbt_today_schedule_day()
        if value is None:
            value = default_day
        try:
            day = int(value)
        except (TypeError, ValueError):
            day = default_day
        if day not in SONOFF_TRVZBT_SCHEDULE_DAY_LOOKUP:
            day = default_day
        if value != day:
            cluster._update_attribute(attrid, day)
        return day
    return value


def _sonoff_trvzbt_format_schedule(transitions):
    """Return the compact schedule text shown in HA."""

    return " ".join(
        f"{minutes // 60:02d}:{minutes % 60:02d}/{heat_setpoint / 100:g}"
        for minutes, heat_setpoint in transitions
    )


def _sonoff_trvzbt_format_minutes(minutes):
    """Format schedule minutes as HH:MM."""

    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def _sonoff_trvzbt_validate_schedule_times(cluster, changed_index=None):
    """Validate local schedule editor transition order."""

    previous_time = None
    for index in range(1, SONOFF_TRVZBT_SCHEDULE_EDITOR_MAX_PERIODS + 1):
        attrid = SONOFF_TRVZBT_SCHEDULE_EDITOR_PERIOD_TIME_ATTRS[index]
        transition_time = _sonoff_trvzbt_uint16(
            _sonoff_trvzbt_get_attr(cluster, attrid),
            f"schedule_period_{index}_time",
        )

        if index == 1 and transition_time == SONOFF_TRVZBT_SCHEDULE_EDITOR_NULL_TIME:
            raise ValueError("weekly schedule time slot 1 must be 00:00")

        if transition_time == SONOFF_TRVZBT_SCHEDULE_EDITOR_NULL_TIME:
            continue

        if transition_time >= 24 * 60:
            raise ValueError(
                f"weekly schedule time slot {index} must be below 24:00 or NULL"
            )

        if index == 1:
            if transition_time != 0:
                raise ValueError("weekly schedule time slot 1 must be 00:00")
        elif previous_time is not None and transition_time <= previous_time:
            minimum_time = previous_time + 30
            raise ValueError(
                f"weekly schedule time slot {index} must be at least "
                f"{_sonoff_trvzbt_format_minutes(minimum_time)} or NULL"
            )

        previous_time = transition_time


def _sonoff_trvzbt_default_schedule(active_num, day_bit):
    """Build a default schedule entry for one group/day pair."""

    active_num = _sonoff_trvzbt_uint8(active_num, "active_num")
    day_bit = _sonoff_trvzbt_uint8(day_bit, "day_of_week")
    transitions = list(SONOFF_TRVZBT_DEFAULT_SCHEDULE_TRANSITIONS)
    return {
        "response_type": "default",
        "schedule_type": 0x01,
        "read_or_write": 0x00,
        "active_num": active_num,
        "transition_count": len(transitions),
        "day_of_week": day_bit,
        "day_name": SONOFF_TRVZBT_SCHEDULE_DAY_LOOKUP.get(
            day_bit, f"unknown_0x{day_bit:02x}"
        ),
        "mode": 0x01,
        "schedule": _sonoff_trvzbt_format_schedule(transitions),
        "editor_transitions": transitions,
        "raw": "",
    }


def _sonoff_trvzbt_build_editor_payload(cluster):
    """Build a schedule write payload from the local HA editor entities."""

    active_num = _sonoff_trvzbt_uint8(
        _sonoff_trvzbt_get_attr(cluster, SONOFF_TRVZBT_SCHEDULE_EDITOR_GROUP_ATTR),
        "schedule_group",
    )
    day_of_week = _sonoff_trvzbt_uint8(
        _sonoff_trvzbt_get_attr(cluster, SONOFF_TRVZBT_SCHEDULE_EDITOR_DAY_ATTR),
        "schedule_operating_day",
    )
    transitions = []
    previous_time = -1
    for index in range(1, SONOFF_TRVZBT_SCHEDULE_EDITOR_MAX_PERIODS + 1):
        transition_time = _sonoff_trvzbt_uint16(
            _sonoff_trvzbt_get_attr(
                cluster, SONOFF_TRVZBT_SCHEDULE_EDITOR_PERIOD_TIME_ATTRS[index]
            ),
            f"schedule_period_{index}_time",
        )
        if index == 1 and transition_time == SONOFF_TRVZBT_SCHEDULE_EDITOR_NULL_TIME:
            raise ValueError("weekly schedule time slot 1 must be 00:00")

        if transition_time == SONOFF_TRVZBT_SCHEDULE_EDITOR_NULL_TIME:
            continue
        if transition_time >= 24 * 60:
            raise ValueError(f"schedule_period_{index}_time must be below 1440")
        if transition_time <= previous_time:
            raise ValueError("schedule period times must be strictly increasing")

        heat_setpoint = _sonoff_trvzbt_int16(
            _sonoff_trvzbt_get_attr(
                cluster, SONOFF_TRVZBT_SCHEDULE_EDITOR_PERIOD_TEMP_ATTRS[index]
            ),
            f"schedule_period_{index}_temperature",
        )
        if heat_setpoint < 500 or heat_setpoint > 3000:
            raise ValueError(f"schedule_period_{index}_temperature must be 5.0-30.0 C")

        transitions.append((transition_time, heat_setpoint))
        previous_time = transition_time

    if not transitions:
        raise ValueError("weekly schedule time slot 1 must be 00:00")

    if transitions[0][0] != 0:
        raise ValueError("the first schedule period must start at 00:00")

    payload = bytes((0x01, 0x01, active_num, len(transitions), day_of_week, 0x01))
    for transition_time, heat_setpoint in transitions:
        payload += transition_time.to_bytes(2, "little")
        payload += heat_setpoint.to_bytes(2, "little", signed=True)

    return payload, active_num, day_of_week, transitions


def _sonoff_trvzbt_update_editor_from_schedule(cluster, schedule):
    """Populate the local schedule editor from a decoded read response."""

    transitions = schedule.get("editor_transitions") or []
    if not transitions:
        return

    selected_day = _sonoff_trvzbt_uint8(
        _sonoff_trvzbt_get_attr(cluster, SONOFF_TRVZBT_SCHEDULE_EDITOR_DAY_ATTR),
        "schedule_editor_day",
    )
    selected_group = _sonoff_trvzbt_uint8(
        _sonoff_trvzbt_get_attr(cluster, SONOFF_TRVZBT_SCHEDULE_EDITOR_GROUP_ATTR),
        "schedule_editor_group",
    )
    if (
        schedule["active_num"] != selected_group
        or not schedule["day_of_week"] & selected_day
    ):
        LOGGER.debug(
            "TRV-ZBT schedule editor ignored group=%s day=0x%02x "
            "selected_group=%s selected_day=0x%02x",
            schedule["active_num"],
            schedule["day_of_week"],
            selected_group,
            selected_day,
        )
        return

    cluster._update_attribute(
        SONOFF_TRVZBT_SCHEDULE_EDITOR_GROUP_ATTR,
        _sonoff_trvzbt_uint8(schedule["active_num"], "active_num"),
    )
    cluster._update_attribute(
        SONOFF_TRVZBT_SCHEDULE_EDITOR_PERIOD_COUNT_ATTR,
        min(len(transitions), SONOFF_TRVZBT_SCHEDULE_EDITOR_MAX_PERIODS),
    )

    editor_transitions = []
    previous_minutes = None
    for minutes, heat_setpoint in transitions[
        :SONOFF_TRVZBT_SCHEDULE_EDITOR_MAX_PERIODS
    ]:
        if minutes == previous_minutes:
            break
        editor_transitions.append((minutes, heat_setpoint))
        previous_minutes = minutes

    for index, (minutes, heat_setpoint) in enumerate(editor_transitions, start=1):
        cluster._update_attribute(
            SONOFF_TRVZBT_SCHEDULE_EDITOR_PERIOD_TIME_ATTRS[index],
            _sonoff_trvzbt_uint16(minutes, f"schedule_period_{index}_time"),
        )
        cluster._update_attribute(
            SONOFF_TRVZBT_SCHEDULE_EDITOR_PERIOD_TEMP_ATTRS[index],
            _sonoff_trvzbt_int16(heat_setpoint, f"schedule_period_{index}_temperature"),
        )

    for index in range(
        len(editor_transitions) + 1, SONOFF_TRVZBT_SCHEDULE_EDITOR_MAX_PERIODS + 1
    ):
        cluster._update_attribute(
            SONOFF_TRVZBT_SCHEDULE_EDITOR_PERIOD_TIME_ATTRS[index],
            SONOFF_TRVZBT_SCHEDULE_EDITOR_NULL_TIME,
        )
        cluster._update_attribute(
            SONOFF_TRVZBT_SCHEDULE_EDITOR_PERIOD_TEMP_ATTRS[index],
            _sonoff_trvzbt_int16(500, f"schedule_period_{index}_temperature"),
        )

    cluster._update_attribute(
        SONOFF_TRVZBT_SCHEDULE_EDITOR_APPLY_STATUS_ATTR, "fetch loaded"
    )


def _sonoff_trvzbt_schedule_cache(cluster):
    """Return the per-group/day schedule cache kept by this cluster instance."""

    cache = getattr(cluster, "_sonoff_trvzbt_schedule_cache", None)
    if cache is None:
        cache = {
            (group, day_bit): _sonoff_trvzbt_default_schedule(group, day_bit)
            for group in SONOFF_TRVZBT_SCHEDULE_GROUP_VALUES
            for day_bit in SONOFF_TRVZBT_SCHEDULE_DAY_BITS
        }
        setattr(cluster, "_sonoff_trvzbt_schedule_cache", cache)
    return cache


def _sonoff_trvzbt_cache_schedule(cluster, schedule):
    """Store decoded schedule data for every day included in the response."""

    cache = _sonoff_trvzbt_schedule_cache(cluster)
    for day_bit in SONOFF_TRVZBT_SCHEDULE_DAY_BITS:
        if schedule["day_of_week"] & day_bit:
            cached_schedule = dict(schedule)
            cached_schedule["day_of_week"] = day_bit
            cached_schedule["day_name"] = SONOFF_TRVZBT_SCHEDULE_DAY_LOOKUP[day_bit]
            cache[(schedule["active_num"], day_bit)] = cached_schedule


def _sonoff_trvzbt_load_cached_schedule(cluster):
    """Reload editor fields from the selected group/day cache."""

    group = _sonoff_trvzbt_uint8(
        _sonoff_trvzbt_get_attr(cluster, SONOFF_TRVZBT_SCHEDULE_EDITOR_GROUP_ATTR),
        "schedule_editor_group",
    )
    day = _sonoff_trvzbt_uint8(
        _sonoff_trvzbt_get_attr(cluster, SONOFF_TRVZBT_SCHEDULE_EDITOR_DAY_ATTR),
        "schedule_editor_day",
    )
    schedule = _sonoff_trvzbt_schedule_cache(cluster).get((group, day))
    if schedule is None:
        return

    _sonoff_trvzbt_update_editor_from_schedule(cluster, schedule)
    LOGGER.debug(
        "TRV-ZBT schedule editor loaded cached group=%s day=0x%02x",
        group,
        day,
    )


def _sonoff_trvzbt_is_replaced_default_entity(entity):
    """Match default ZHA entities replaced by custom definitions."""

    cluster_id = getattr(entity, "cluster_id", None)
    unique_id_suffix = getattr(entity, "unique_id_suffix", None)
    if unique_id_suffix == "local_temperature_calibration" and cluster_id in (
        None,
        SonoffThermostat.cluster_id,
    ):
        return True

    needles = (
        "local_temperature_calibration",
        "min_heat_setpoint_limit",
        "max_heat_setpoint_limit",
    )
    fields = (
        "unique_id",
        "unique_id_suffix",
        "translation_key",
        "fallback_name",
        "attribute_name",
        "name",
    )
    for field in fields:
        value = getattr(entity, field, None)
        if value is None:
            continue

        normalized_value = str(value).lower().replace(" ", "_")
        if any(needle in normalized_value for needle in needles):
            return True
    return False


class SonoffThermostat(CustomCluster, Thermostat):
    """Thermostat cluster with TRV-ZBT system modes."""

    class AttributeDefs(Thermostat.AttributeDefs):
        """TRV-ZBT thermostat attributes."""

        system_mode = ZCLAttributeDef(
            id=Thermostat.AttributeDefs.system_mode.id,
            type=SonoffSystemMode,
            zcl_type=DataTypeId.enum8,
            access=Thermostat.AttributeDefs.system_mode.access,
            mandatory=Thermostat.AttributeDefs.system_mode.mandatory,
            manufacturer_code=Thermostat.AttributeDefs.system_mode.manufacturer_code,
        )
        min_heat_setpoint_limit = ZCLAttributeDef(
            id=Thermostat.AttributeDefs.min_heat_setpoint_limit.id,
            type=t.int16s,
            access="r",
            mandatory=Thermostat.AttributeDefs.min_heat_setpoint_limit.mandatory,
            manufacturer_code=Thermostat.AttributeDefs.min_heat_setpoint_limit.manufacturer_code,
        )
        max_heat_setpoint_limit = ZCLAttributeDef(
            id=Thermostat.AttributeDefs.max_heat_setpoint_limit.id,
            type=t.int16s,
            access="r",
            mandatory=Thermostat.AttributeDefs.max_heat_setpoint_limit.mandatory,
            manufacturer_code=Thermostat.AttributeDefs.max_heat_setpoint_limit.manufacturer_code,
        )

    def _is_boost_mode_active(self):
        """Return whether the paired private cluster currently reports Boost."""

        private_cluster = getattr(self.endpoint, "in_clusters", {}).get(
            SONOFF_TRVZBT_PRIVATE_CLUSTER_ID
        )
        if private_cluster is None:
            return False

        value = getattr(private_cluster, "_attr_cache", {}).get(
            SONOFF_TRVZBT_TEMPORARY_MODE_ATTR
        )
        if value is None:
            return False

        try:
            return int(value) == int(SonoffTemporaryMode.Boost)
        except (TypeError, ValueError):
            return False

    async def sonoff_trvzbt_send_setpoint_signal(
        self, setpoint=None, manufacturer=None, **kwargs
    ):
        """Send a setpoint write signal so the device exits temporary mode."""

        setpoint_attr = self.AttributeDefs.occupied_heating_setpoint
        if setpoint is None:
            setpoint = self._attr_cache.get(setpoint_attr.id)
        if setpoint is None:
            success, _ = await self.read_attributes(
                [setpoint_attr.name], allow_cache=False, manufacturer=manufacturer
            )
            setpoint = success.get(setpoint_attr.name)
            if setpoint is None:
                setpoint = success.get(setpoint_attr.id)

        setpoint = _sonoff_trvzbt_int16(setpoint, "occupied_heating_setpoint")
        await super().write_attributes(
            {setpoint_attr.name: setpoint}, manufacturer=manufacturer, **kwargs
        )
        self._update_attribute(setpoint_attr.id, setpoint)
        return setpoint

    async def write_attributes(self, attributes, manufacturer=None, **kwargs):
        """Block HA target-temperature writes while device is in Boost mode."""

        setpoint_name = self.AttributeDefs.occupied_heating_setpoint.name
        setpoint_id = self.AttributeDefs.occupied_heating_setpoint.id
        if (
            setpoint_name in attributes or setpoint_id in attributes
        ) and self._is_boost_mode_active():
            raise ValueError(
                "occupied_heating_setpoint cannot be changed while Boost mode is active"
            )

        return await super().write_attributes(
            attributes, manufacturer=manufacturer, **kwargs
        )


class SonoffBasicCluster(CustomCluster, Basic):
    """Basic cluster with firmware-related attributes exposed."""


class CustomSonoffCluster(CustomCluster):
    """Custom Sonoff cluster."""

    cluster_id = SONOFF_TRVZBT_PRIVATE_CLUSTER_ID
    ep_attribute = "sonoff_trv_zbt"

    def __init__(self, *args, **kwargs):
        """Initialize virtual editor state and delayed state refreshes."""
        super().__init__(*args, **kwargs)
        for attrid, value in SONOFF_TRVZBT_SCHEDULE_EDITOR_DEFAULTS.items():
            self._update_attribute(attrid, value)
        self._update_attribute(
            SONOFF_TRVZBT_SCHEDULE_EDITOR_DAY_ATTR,
            _sonoff_trvzbt_today_schedule_day(),
        )
        self._update_attribute(
            self.AttributeDefs.motor_travel_calibration_status.id, 0x00
        )
        self._update_attribute(
            self.AttributeDefs.temporary_mode.id, SonoffTemporaryMode.None_
        )
        self._sonoff_trvzbt_temporary_mode_read_task = None
        self._sonoff_trvzbt_device_work_mode_read_task = None
        self._sonoff_trvzbt_pre_temporary_state = None
        self._sonoff_trvzbt_schedule_temporary_mode_read(delay=60)
        self._sonoff_trvzbt_schedule_device_work_mode_read(delay=60)

    def _update_attribute(self, attrid, value):
        """Keep the temporary-mode editor in sync with the device-reported state."""

        super()._update_attribute(attrid, value)
        if attrid != self.AttributeDefs.temporary_mode.id:
            return

        try:
            mode = int(value)
        except (TypeError, ValueError):
            return

        editor_mode = None
        if mode == int(SonoffTemporaryMode.Boost):
            editor_mode = SonoffTemporaryModeEditor.Boost
        elif mode == int(SonoffTemporaryMode.Timer):
            editor_mode = SonoffTemporaryModeEditor.Timer
        elif mode == int(SonoffTemporaryMode.None_):
            editor_mode = SonoffTemporaryModeEditor.None_

        if editor_mode is not None:
            super()._update_attribute(
                SONOFF_TRVZBT_TEMPORARY_MODE_EDITOR_MODE_ATTR, editor_mode
            )

    async def _sonoff_trvzbt_capture_pre_temporary_state(self, manufacturer=None):
        """Cache the state that should be restored when temporary mode exits."""

        if self._sonoff_trvzbt_pre_temporary_state is not None:
            return

        current_mode = self._attr_cache.get(self.AttributeDefs.temporary_mode.id)
        try:
            if int(current_mode) in (
                int(SonoffTemporaryMode.Boost),
                int(SonoffTemporaryMode.Timer),
            ):
                return
        except (TypeError, ValueError):
            pass

        thermostat_cluster = getattr(self.endpoint, "in_clusters", {}).get(
            SonoffThermostat.cluster_id
        )
        if thermostat_cluster is None:
            return

        setpoint_attr = SonoffThermostat.AttributeDefs.occupied_heating_setpoint
        system_mode_attr = SonoffThermostat.AttributeDefs.system_mode
        setpoint = thermostat_cluster._attr_cache.get(setpoint_attr.id)
        system_mode = thermostat_cluster._attr_cache.get(system_mode_attr.id)

        missing = []
        if setpoint is None:
            missing.append(setpoint_attr.name)
        if system_mode is None:
            missing.append(system_mode_attr.name)
        if missing:
            try:
                success, _ = await thermostat_cluster.read_attributes(
                    missing, allow_cache=False, manufacturer=manufacturer
                )
            except Exception as exc:
                LOGGER.warning("TRV-ZBT pre-temporary state read failed: %s", exc)
                success = {}
            if setpoint is None:
                setpoint = success.get(
                    setpoint_attr.name, success.get(setpoint_attr.id)
                )
            if system_mode is None:
                system_mode = success.get(
                    system_mode_attr.name, success.get(system_mode_attr.id)
                )

        self._sonoff_trvzbt_pre_temporary_state = {
            "occupied_heating_setpoint": setpoint,
            "system_mode": system_mode,
        }
        LOGGER.info(
            "TRV-ZBT captured pre-temporary state: occupied_heating_setpoint=%s "
            "system_mode=%s",
            setpoint,
            system_mode,
        )

    def _sonoff_trvzbt_schedule_temporary_mode_read(self, delay=60):
        """Schedule a delayed read of the current temporary mode."""

        super()._update_attribute(
            self.AttributeDefs.temporary_mode.id, SonoffTemporaryMode.None_
        )
        task = getattr(self, "_sonoff_trvzbt_temporary_mode_read_task", None)
        if task is not None and not task.done():
            return
        self._sonoff_trvzbt_temporary_mode_read_task = asyncio.create_task(
            self._sonoff_trvzbt_read_temporary_mode_later(delay=delay)
        )

    def _sonoff_trvzbt_schedule_device_work_mode_read(self, delay=60):
        """Schedule a delayed read of the current device work mode."""

        task = getattr(self, "_sonoff_trvzbt_device_work_mode_read_task", None)
        if task is not None and not task.done():
            return
        self._sonoff_trvzbt_device_work_mode_read_task = asyncio.create_task(
            self._sonoff_trvzbt_read_device_work_mode_later(delay=delay)
        )

    async def _sonoff_trvzbt_read_temporary_mode_later(self, delay=60):
        """Read 0x6014 after join/startup because the device may not report it."""

        attr_name = self.AttributeDefs.temporary_mode.name
        for attempt in range(1, 4):
            await asyncio.sleep(delay)
            try:
                success, failure = await self.read_attributes(
                    [attr_name], allow_cache=False
                )
            except Exception as exc:
                LOGGER.warning(
                    "TRV-ZBT temporary mode read attempt %s failed: %s",
                    attempt,
                    exc,
                )
                continue

            if attr_name in success:
                LOGGER.info(
                    "TRV-ZBT temporary mode read success on attempt %s: %s",
                    attempt,
                    success[attr_name],
                )
                return

            LOGGER.info(
                "TRV-ZBT temporary mode read attempt %s no value: success=%s failure=%s",
                attempt,
                success,
                failure,
            )

    async def _sonoff_trvzbt_read_device_work_mode_later(self, delay=60):
        """Read 0x0018 after join/startup because the device may not report it."""

        attr_name = self.AttributeDefs.device_work_mode.name
        for attempt in range(1, 4):
            await asyncio.sleep(delay)
            try:
                success, failure = await self.read_attributes(
                    [attr_name], allow_cache=False
                )
            except Exception as exc:
                LOGGER.warning(
                    "TRV-ZBT device work mode read attempt %s failed: %s",
                    attempt,
                    exc,
                )
                continue

            if attr_name in success:
                LOGGER.info(
                    "TRV-ZBT device work mode read success on attempt %s: %s",
                    attempt,
                    success[attr_name],
                )
                return

            LOGGER.info(
                "TRV-ZBT device work mode read attempt %s no value: success=%s failure=%s",
                attempt,
                success,
                failure,
            )

        LOGGER.warning("TRV-ZBT device work mode read failed; keeping cached state")

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        child_lock = ZCLAttributeDef(
            id=0x0000,
            type=t.Bool,
            manufacturer_code=None,
        )
        fault_code = ZCLAttributeDef(
            id=0x0010,
            type=t.uint32_t,
            access="r",
            manufacturer_code=None,
        )
        device_work_mode = ZCLAttributeDef(
            id=0x0018,
            type=SonoffDeviceWorkMode,
            zcl_type=DataTypeId.uint8,
            access="r",
            manufacturer_code=None,
        )
        screen_direction = ZCLAttributeDef(
            id=0x0021,
            type=SonoffScreenDirection,
            zcl_type=DataTypeId.uint8,
            manufacturer_code=None,
        )
        open_window = ZCLAttributeDef(
            id=0x6000,
            type=t.Bool,
            manufacturer_code=None,
        )
        frost_protection_temperature = ZCLAttributeDef(
            id=0x6002,
            type=t.int16s,
            manufacturer_code=None,
        )

        idle_steps = ZCLAttributeDef(
            id=0x6003,
            type=t.uint16_t,
            access="r",
            manufacturer_code=None,
        )
        closing_steps = ZCLAttributeDef(
            id=0x6004,
            type=t.uint16_t,
            access="r",
            manufacturer_code=None,
        )
        valve_opening_limit_voltage = ZCLAttributeDef(
            id=0x6005,
            type=t.uint16_t,
            access="r",
            manufacturer_code=None,
        )
        valve_closing_limit_voltage = ZCLAttributeDef(
            id=0x6006,
            type=t.uint16_t,
            access="r",
            manufacturer_code=None,
        )
        valve_motor_running_voltage = ZCLAttributeDef(
            id=0x6007,
            type=t.uint16_t,
            access="r",
            manufacturer_code=None,
        )

        weekly_program_state = ZCLAttributeDef(
            id=0x6008,
            type=t.uint8_t,
            manufacturer_code=None,
        )
        manual_mode_temperature = ZCLAttributeDef(
            id=0x6009,
            type=t.int16s,
            manufacturer_code=None,
        )
        auto_mode_temperature = ZCLAttributeDef(
            id=0x600A,
            type=t.int16s,
            manufacturer_code=None,
        )
        valve_opening_degree = ZCLAttributeDef(
            id=0x600B,
            type=t.uint8_t,
            manufacturer_code=None,
        )
        valve_closing_degree = ZCLAttributeDef(
            id=0x600C,
            type=t.uint8_t,
            manufacturer_code=None,
        )

        temperature_sensor_select = ZCLAttributeDef(
            id=0x600E,
            type=SonoffTemperatureSensorSelect,
            zcl_type=DataTypeId.uint8,
            manufacturer_code=None,
        )
        external_temperature_sensor_value = ZCLAttributeDef(
            id=0x600D,
            type=t.int16s,
            manufacturer_code=None,
        )
        temperature_control_accuracy = ZCLAttributeDef(
            id=0x6011,
            type=t.int16s,
            manufacturer_code=None,
        )
        temperature_trigger_of_valve_closing = ZCLAttributeDef(
            id=0x6012,
            type=t.int16s,
            manufacturer_code=None,
        )
        temperature_control_mode = ZCLAttributeDef(
            id=0x6013,
            type=t.enum8,
            manufacturer_code=None,
        )

        temporary_mode = ZCLAttributeDef(
            id=SONOFF_TRVZBT_TEMPORARY_MODE_ATTR,
            type=SonoffTemporaryMode,
            zcl_type=DataTypeId.uint8,
            manufacturer_code=None,
        )
        temporary_mode_duration = ZCLAttributeDef(
            id=0x6015,
            type=t.uint32_t,
            manufacturer_code=None,
        )
        timer_mode_target_temperature = ZCLAttributeDef(
            id=0x6016,
            type=t.int16s,
            manufacturer_code=None,
        )
        low_battery_valve_state = ZCLAttributeDef(
            id=0x601C,
            type=SonoffLowBatteryValveState,
            zcl_type=DataTypeId.uint8,
            manufacturer_code=None,
        )
        weekly_schedule_active_num = ZCLAttributeDef(
            id=0x601D,
            type=t.uint8_t,
            manufacturer_code=None,
        )

        hvac_message_notification = ZCLAttributeDef(
            id=0x6030,
            type=SonoffHvacMessageNotification,
            zcl_type=DataTypeId.array,
            access="r",
            manufacturer_code=None,
        )
        heat_percentage_hour = ZCLAttributeDef(
            id=0x6033,
            type=t.uint8_t,
            access="r",
            manufacturer_code=None,
        )
        motor_travel_calibration = ZCLAttributeDef(
            id=0x6036,
            type=t.Bool,
            access="w",
            manufacturer_code=None,
        )
        motor_travel_calibration_status = ZCLAttributeDef(
            id=0x6037,
            type=SonoffMotorTravelCalibrationStatus,
            zcl_type=DataTypeId.uint8,
            access="rp",
            manufacturer_code=None,
        )

        weekly_schedule_sunday = ZCLAttributeDef(
            id=SONOFF_TRVZBT_SCHEDULE_ATTR_BY_DAY[0x01],
            type=t.CharacterString,
            access="r",
            manufacturer_code=None,
        )
        weekly_schedule_monday = ZCLAttributeDef(
            id=SONOFF_TRVZBT_SCHEDULE_ATTR_BY_DAY[0x02],
            type=t.CharacterString,
            access="r",
            manufacturer_code=None,
        )
        weekly_schedule_tuesday = ZCLAttributeDef(
            id=SONOFF_TRVZBT_SCHEDULE_ATTR_BY_DAY[0x04],
            type=t.CharacterString,
            access="r",
            manufacturer_code=None,
        )
        weekly_schedule_wednesday = ZCLAttributeDef(
            id=SONOFF_TRVZBT_SCHEDULE_ATTR_BY_DAY[0x08],
            type=t.CharacterString,
            access="r",
            manufacturer_code=None,
        )
        weekly_schedule_thursday = ZCLAttributeDef(
            id=SONOFF_TRVZBT_SCHEDULE_ATTR_BY_DAY[0x10],
            type=t.CharacterString,
            access="r",
            manufacturer_code=None,
        )
        weekly_schedule_friday = ZCLAttributeDef(
            id=SONOFF_TRVZBT_SCHEDULE_ATTR_BY_DAY[0x20],
            type=t.CharacterString,
            access="r",
            manufacturer_code=None,
        )
        weekly_schedule_saturday = ZCLAttributeDef(
            id=SONOFF_TRVZBT_SCHEDULE_ATTR_BY_DAY[0x40],
            type=t.CharacterString,
            access="r",
            manufacturer_code=None,
        )
        weekly_schedule_status = ZCLAttributeDef(
            id=SONOFF_TRVZBT_SCHEDULE_STATUS_ATTR,
            type=t.CharacterString,
            access="r",
            manufacturer_code=None,
        )
        bluetooth_pairing_status = ZCLAttributeDef(
            id=SONOFF_TRVZBT_BLUETOOTH_PAIRING_STATUS_ATTR,
            type=t.CharacterString,
            access="r",
            manufacturer_code=None,
        )
        bluetooth_pairing_request = ZCLAttributeDef(
            id=SONOFF_TRVZBT_BLUETOOTH_PAIRING_REQUEST_ATTR,
            type=t.Bool,
            manufacturer_code=None,
        )
        local_temperature_offset = ZCLAttributeDef(
            id=SONOFF_TRVZBT_LOCAL_TEMPERATURE_OFFSET_ATTR,
            type=t.int16s,
            manufacturer_code=None,
        )
        temporary_mode_editor_mode = ZCLAttributeDef(
            id=SONOFF_TRVZBT_TEMPORARY_MODE_EDITOR_MODE_ATTR,
            type=SonoffTemporaryModeEditor,
            zcl_type=DataTypeId.uint8,
            manufacturer_code=None,
        )
        temporary_mode_editor_duration = ZCLAttributeDef(
            id=SONOFF_TRVZBT_TEMPORARY_MODE_EDITOR_DURATION_ATTR,
            type=t.uint32_t,
            manufacturer_code=None,
        )
        temporary_mode_editor_target_temperature = ZCLAttributeDef(
            id=SONOFF_TRVZBT_TEMPORARY_MODE_EDITOR_TARGET_TEMPERATURE_ATTR,
            type=t.int16s,
            manufacturer_code=None,
        )
        temporary_mode_editor_apply_status = ZCLAttributeDef(
            id=SONOFF_TRVZBT_TEMPORARY_MODE_EDITOR_APPLY_STATUS_ATTR,
            type=t.CharacterString,
            access="r",
            manufacturer_code=None,
        )
        schedule_editor_group = ZCLAttributeDef(
            id=SONOFF_TRVZBT_SCHEDULE_EDITOR_GROUP_ATTR,
            type=SonoffScheduleGroup,
            zcl_type=DataTypeId.uint8,
            manufacturer_code=None,
        )
        schedule_editor_day = ZCLAttributeDef(
            id=SONOFF_TRVZBT_SCHEDULE_EDITOR_DAY_ATTR,
            type=SonoffScheduleDay,
            zcl_type=DataTypeId.uint8,
            manufacturer_code=None,
        )
        schedule_editor_period_count = ZCLAttributeDef(
            id=SONOFF_TRVZBT_SCHEDULE_EDITOR_PERIOD_COUNT_ATTR,
            type=t.uint8_t,
            manufacturer_code=None,
        )
        schedule_editor_apply_status = ZCLAttributeDef(
            id=SONOFF_TRVZBT_SCHEDULE_EDITOR_APPLY_STATUS_ATTR,
            type=t.CharacterString,
            access="r",
            manufacturer_code=None,
        )
        schedule_period_1_time = ZCLAttributeDef(
            id=SONOFF_TRVZBT_SCHEDULE_EDITOR_PERIOD_TIME_ATTRS[1],
            type=SonoffScheduleTime,
            zcl_type=DataTypeId.enum16,
            manufacturer_code=None,
        )
        schedule_period_2_time = ZCLAttributeDef(
            id=SONOFF_TRVZBT_SCHEDULE_EDITOR_PERIOD_TIME_ATTRS[2],
            type=SonoffScheduleTime,
            zcl_type=DataTypeId.enum16,
            manufacturer_code=None,
        )
        schedule_period_3_time = ZCLAttributeDef(
            id=SONOFF_TRVZBT_SCHEDULE_EDITOR_PERIOD_TIME_ATTRS[3],
            type=SonoffScheduleTime,
            zcl_type=DataTypeId.enum16,
            manufacturer_code=None,
        )
        schedule_period_4_time = ZCLAttributeDef(
            id=SONOFF_TRVZBT_SCHEDULE_EDITOR_PERIOD_TIME_ATTRS[4],
            type=SonoffScheduleTime,
            zcl_type=DataTypeId.enum16,
            manufacturer_code=None,
        )
        schedule_period_5_time = ZCLAttributeDef(
            id=SONOFF_TRVZBT_SCHEDULE_EDITOR_PERIOD_TIME_ATTRS[5],
            type=SonoffScheduleTime,
            zcl_type=DataTypeId.enum16,
            manufacturer_code=None,
        )
        schedule_period_6_time = ZCLAttributeDef(
            id=SONOFF_TRVZBT_SCHEDULE_EDITOR_PERIOD_TIME_ATTRS[6],
            type=SonoffScheduleTime,
            zcl_type=DataTypeId.enum16,
            manufacturer_code=None,
        )
        schedule_period_7_time = ZCLAttributeDef(
            id=SONOFF_TRVZBT_SCHEDULE_EDITOR_PERIOD_TIME_ATTRS[7],
            type=SonoffScheduleTime,
            zcl_type=DataTypeId.enum16,
            manufacturer_code=None,
        )
        schedule_period_8_time = ZCLAttributeDef(
            id=SONOFF_TRVZBT_SCHEDULE_EDITOR_PERIOD_TIME_ATTRS[8],
            type=SonoffScheduleTime,
            zcl_type=DataTypeId.enum16,
            manufacturer_code=None,
        )
        schedule_period_9_time = ZCLAttributeDef(
            id=SONOFF_TRVZBT_SCHEDULE_EDITOR_PERIOD_TIME_ATTRS[9],
            type=SonoffScheduleTime,
            zcl_type=DataTypeId.enum16,
            manufacturer_code=None,
        )
        schedule_period_10_time = ZCLAttributeDef(
            id=SONOFF_TRVZBT_SCHEDULE_EDITOR_PERIOD_TIME_ATTRS[10],
            type=SonoffScheduleTime,
            zcl_type=DataTypeId.enum16,
            manufacturer_code=None,
        )
        schedule_period_11_time = ZCLAttributeDef(
            id=SONOFF_TRVZBT_SCHEDULE_EDITOR_PERIOD_TIME_ATTRS[11],
            type=SonoffScheduleTime,
            zcl_type=DataTypeId.enum16,
            manufacturer_code=None,
        )
        schedule_period_12_time = ZCLAttributeDef(
            id=SONOFF_TRVZBT_SCHEDULE_EDITOR_PERIOD_TIME_ATTRS[12],
            type=SonoffScheduleTime,
            zcl_type=DataTypeId.enum16,
            manufacturer_code=None,
        )
        schedule_period_1_temperature = ZCLAttributeDef(
            id=SONOFF_TRVZBT_SCHEDULE_EDITOR_PERIOD_TEMP_ATTRS[1],
            type=t.int16s,
            manufacturer_code=None,
        )
        schedule_period_2_temperature = ZCLAttributeDef(
            id=SONOFF_TRVZBT_SCHEDULE_EDITOR_PERIOD_TEMP_ATTRS[2],
            type=t.int16s,
            manufacturer_code=None,
        )
        schedule_period_3_temperature = ZCLAttributeDef(
            id=SONOFF_TRVZBT_SCHEDULE_EDITOR_PERIOD_TEMP_ATTRS[3],
            type=t.int16s,
            manufacturer_code=None,
        )
        schedule_period_4_temperature = ZCLAttributeDef(
            id=SONOFF_TRVZBT_SCHEDULE_EDITOR_PERIOD_TEMP_ATTRS[4],
            type=t.int16s,
            manufacturer_code=None,
        )
        schedule_period_5_temperature = ZCLAttributeDef(
            id=SONOFF_TRVZBT_SCHEDULE_EDITOR_PERIOD_TEMP_ATTRS[5],
            type=t.int16s,
            manufacturer_code=None,
        )
        schedule_period_6_temperature = ZCLAttributeDef(
            id=SONOFF_TRVZBT_SCHEDULE_EDITOR_PERIOD_TEMP_ATTRS[6],
            type=t.int16s,
            manufacturer_code=None,
        )
        schedule_period_7_temperature = ZCLAttributeDef(
            id=SONOFF_TRVZBT_SCHEDULE_EDITOR_PERIOD_TEMP_ATTRS[7],
            type=t.int16s,
            manufacturer_code=None,
        )
        schedule_period_8_temperature = ZCLAttributeDef(
            id=SONOFF_TRVZBT_SCHEDULE_EDITOR_PERIOD_TEMP_ATTRS[8],
            type=t.int16s,
            manufacturer_code=None,
        )
        schedule_period_9_temperature = ZCLAttributeDef(
            id=SONOFF_TRVZBT_SCHEDULE_EDITOR_PERIOD_TEMP_ATTRS[9],
            type=t.int16s,
            manufacturer_code=None,
        )
        schedule_period_10_temperature = ZCLAttributeDef(
            id=SONOFF_TRVZBT_SCHEDULE_EDITOR_PERIOD_TEMP_ATTRS[10],
            type=t.int16s,
            manufacturer_code=None,
        )
        schedule_period_11_temperature = ZCLAttributeDef(
            id=SONOFF_TRVZBT_SCHEDULE_EDITOR_PERIOD_TEMP_ATTRS[11],
            type=t.int16s,
            manufacturer_code=None,
        )
        schedule_period_12_temperature = ZCLAttributeDef(
            id=SONOFF_TRVZBT_SCHEDULE_EDITOR_PERIOD_TEMP_ATTRS[12],
            type=t.int16s,
            manufacturer_code=None,
        )

    class ServerCommandDefs(BaseCommandDefs):
        """Commands sent from HA to the device."""

        bluetooth_pairing = ZCLCommandDef(
            id=0x10,
            schema={
                "prefix": t.uint8_t,
                "action": t.uint8_t,
                "event_type": t.uint8_t,
            },
            manufacturer_code=None,
        )
        schedule_apply = ZCLCommandDef(
            id=0xF1,
            schema={},
            manufacturer_code=None,
        )
        schedule_group = ZCLCommandDef(
            id=0x13,
            schema=SonoffScheduleGroupCommand,
            manufacturer_code=None,
        )
        schedule_group_raw = ZCLCommandDef(
            id=0x13,
            schema={"data": SonoffRawBytes},
            manufacturer_code=None,
        )

    class ClientCommandDefs(BaseCommandDefs):
        """Commands sent from the device to HA."""

        bluetooth_pairing_response = ZCLCommandDef(
            id=0x10,
            schema={
                "prefix": t.uint8_t,
                "status": t.uint8_t,
            },
            manufacturer_code=None,
        )

    async def schedule_apply(self, expect_reply=False):
        """Write the schedule currently configured in the local editor."""

        payload, active_num, day_of_week, transitions = (
            _sonoff_trvzbt_build_editor_payload(self)
        )
        await self.schedule_group_raw(data=payload, expect_reply=expect_reply)
        self._update_attribute(
            SONOFF_TRVZBT_SCHEDULE_EDITOR_APPLY_STATUS_ATTR, "apply sent"
        )
        LOGGER.info(
            "TRV-ZBT schedule editor apply: active=%s day=0x%02x "
            "transitions=%s payload=%s",
            active_num,
            day_of_week,
            transitions,
            payload.hex(" "),
        )

    async def schedule_fetch(self, expect_reply=False):
        """Read the schedule group selected in the local editor."""

        active_num = _sonoff_trvzbt_uint8(
            _sonoff_trvzbt_get_attr(self, SONOFF_TRVZBT_SCHEDULE_EDITOR_GROUP_ATTR),
            "schedule_group",
        )
        selected_day = _sonoff_trvzbt_uint8(
            _sonoff_trvzbt_get_attr(self, SONOFF_TRVZBT_SCHEDULE_EDITOR_DAY_ATTR),
            "schedule_operating_day",
        )
        payload = bytes((0x01, 0x00, active_num))
        await self.schedule_group_raw(data=payload, expect_reply=expect_reply)
        self._update_attribute(
            SONOFF_TRVZBT_SCHEDULE_EDITOR_APPLY_STATUS_ATTR, "fetch sent"
        )
        LOGGER.info(
            "TRV-ZBT schedule editor fetch: active=%s selected_day=0x%02x payload=%s",
            active_num,
            selected_day,
            payload.hex(" "),
        )

    async def temporary_mode_apply(self, expect_reply=False):
        """Apply the locally edited temporary mode settings to the device."""

        await asyncio.sleep(0.2)

        editor_mode = _sonoff_trvzbt_uint8(
            _sonoff_trvzbt_get_attr(
                self, SONOFF_TRVZBT_TEMPORARY_MODE_EDITOR_MODE_ATTR
            ),
            "temporary_mode",
        )
        if editor_mode == int(SonoffTemporaryModeEditor.Boost):
            mode = int(SonoffTemporaryMode.Boost)
        elif editor_mode == int(SonoffTemporaryModeEditor.Timer):
            mode = int(SonoffTemporaryMode.Timer)
        elif editor_mode == int(SonoffTemporaryModeEditor.None_):
            await self.temporary_mode_exit(expect_reply=expect_reply)
            return
        else:
            raise ValueError("temporary_mode must be None, Boost or Timer")
        duration_seconds = int(
            _sonoff_trvzbt_get_attr(
                self, SONOFF_TRVZBT_TEMPORARY_MODE_EDITOR_DURATION_ATTR
            )
        )
        target_temperature = _sonoff_trvzbt_int16(
            _sonoff_trvzbt_get_attr(
                self,
                SONOFF_TRVZBT_TEMPORARY_MODE_EDITOR_TARGET_TEMPERATURE_ATTR,
            ),
            "timer_mode_target_temperature",
        )

        if duration_seconds < 0:
            raise ValueError("temporary_mode_duration must not be negative")
        if duration_seconds % 60 != 0:
            raise ValueError(
                "temporary_mode_duration must be a whole number of minutes"
            )

        await self._sonoff_trvzbt_capture_pre_temporary_state()

        duration_attr = self.AttributeDefs.temporary_mode_duration
        mode_attr = self.AttributeDefs.temporary_mode
        if mode == int(SonoffTemporaryMode.Boost):
            max_seconds = 180 * 60
            if duration_seconds > max_seconds:
                duration_seconds = max_seconds
                self._update_attribute(
                    SONOFF_TRVZBT_TEMPORARY_MODE_EDITOR_DURATION_ATTR,
                    duration_seconds,
                )
            if duration_seconds == 0:
                await super().write_attributes(
                    {
                        duration_attr.name: duration_seconds,
                        mode_attr.name: mode,
                    }
                )
                self._update_attribute(mode_attr.id, mode)
                LOGGER.info("TRV-ZBT Boost apply sent zero duration")
            else:
                alternate_duration = (
                    duration_seconds + 60
                    if duration_seconds < max_seconds
                    else duration_seconds - 60
                )
                await super().write_attributes(
                    {
                        duration_attr.name: alternate_duration,
                        mode_attr.name: mode,
                    }
                )
                self._update_attribute(duration_attr.id, alternate_duration)
                self._update_attribute(mode_attr.id, mode)
                await super().write_attributes({duration_attr.name: duration_seconds})
                LOGGER.info(
                    "TRV-ZBT Boost apply forced duration refresh: alternate=%s target=%s",
                    alternate_duration,
                    duration_seconds,
                )
            self._update_attribute(duration_attr.id, duration_seconds)
        else:
            max_seconds = 1440 * 60
            if duration_seconds > max_seconds:
                raise ValueError(
                    "temporary_mode_duration must be 0-1440 minutes while Timer mode is active"
                )
            if target_temperature < 500 or target_temperature > 3000:
                raise ValueError("timer_mode_target_temperature must be 5-30 C")
            await super().write_attributes(
                {
                    self.AttributeDefs.timer_mode_target_temperature.name: target_temperature,
                }
            )
            self._update_attribute(
                self.AttributeDefs.timer_mode_target_temperature.id, target_temperature
            )
            await super().write_attributes({duration_attr.name: duration_seconds})
            self._update_attribute(duration_attr.id, duration_seconds)
            await super().write_attributes({mode_attr.name: mode})
            self._update_attribute(mode_attr.id, mode)
        self._update_attribute(
            SONOFF_TRVZBT_TEMPORARY_MODE_EDITOR_APPLY_STATUS_ATTR, "apply sent"
        )
        LOGGER.info(
            "TRV-ZBT temporary mode apply: mode=%s duration_seconds=%s target_temperature=%s",
            mode,
            duration_seconds,
            target_temperature,
        )

    async def temporary_mode_exit(self, expect_reply=False):
        """Exit temporary mode by sending the current thermostat setpoint."""

        thermostat_cluster = getattr(self.endpoint, "in_clusters", {}).get(
            SonoffThermostat.cluster_id
        )
        if thermostat_cluster is None:
            raise ValueError("thermostat cluster is not available")

        pre_state = self._sonoff_trvzbt_pre_temporary_state or {}
        restore_setpoint = pre_state.get("occupied_heating_setpoint")
        restore_system_mode = pre_state.get("system_mode")

        setpoint = await thermostat_cluster.sonoff_trvzbt_send_setpoint_signal(
            setpoint=restore_setpoint
        )
        restored_system_mode = False
        if restore_system_mode is not None:
            system_mode_attr = SonoffThermostat.AttributeDefs.system_mode
            try:
                await asyncio.sleep(0.2)
                await thermostat_cluster.write_attributes(
                    {system_mode_attr.name: restore_system_mode}
                )
                thermostat_cluster._update_attribute(
                    system_mode_attr.id, restore_system_mode
                )
                restored_system_mode = True
            except Exception as exc:
                LOGGER.warning(
                    "TRV-ZBT temporary mode exit: failed to restore system_mode=%s: %s",
                    restore_system_mode,
                    exc,
                )
        self._update_attribute(
            self.AttributeDefs.temporary_mode.id, SonoffTemporaryMode.None_
        )
        self._update_attribute(self.AttributeDefs.temporary_mode_duration.id, 0)
        self._update_attribute(SONOFF_TRVZBT_TEMPORARY_MODE_EDITOR_DURATION_ATTR, 0)
        self._update_attribute(
            SONOFF_TRVZBT_TEMPORARY_MODE_EDITOR_APPLY_STATUS_ATTR, "exit sent"
        )
        self._sonoff_trvzbt_schedule_temporary_mode_read(delay=5)
        self._sonoff_trvzbt_schedule_device_work_mode_read(delay=5)
        if restore_system_mode is None or restored_system_mode:
            self._sonoff_trvzbt_pre_temporary_state = None
        LOGGER.info(
            "TRV-ZBT temporary mode exit: sent occupied_heating_setpoint=%s "
            "restore_system_mode=%s",
            setpoint,
            restore_system_mode,
        )

    async def bluetooth_pairing_press(self, expect_reply=False):
        """Start Bluetooth pairing once."""

        self._sonoff_trvzbt_pending_bluetooth_pairing_request = True
        await self.bluetooth_pairing(
            prefix=0x03,
            action=0x01,
            event_type=0x01,
            expect_reply=expect_reply,
        )
        self._update_attribute(SONOFF_TRVZBT_BLUETOOTH_PAIRING_STATUS_ATTR, "sent")
        LOGGER.info("TRV-ZBT bluetooth pairing command sent")

    async def read_attributes(
        self, attributes, allow_cache=False, only_cache=False, manufacturer=None
    ):
        """Return local virtual attributes from cache instead of reading the device."""

        local_attr_ids = {
            SONOFF_TRVZBT_SCHEDULE_STATUS_ATTR,
            SONOFF_TRVZBT_BLUETOOTH_PAIRING_STATUS_ATTR,
            SONOFF_TRVZBT_BLUETOOTH_PAIRING_REQUEST_ATTR,
            SONOFF_TRVZBT_SCHEDULE_EDITOR_GROUP_ATTR,
            SONOFF_TRVZBT_SCHEDULE_EDITOR_DAY_ATTR,
            SONOFF_TRVZBT_SCHEDULE_EDITOR_PERIOD_COUNT_ATTR,
            SONOFF_TRVZBT_SCHEDULE_EDITOR_APPLY_STATUS_ATTR,
            SONOFF_TRVZBT_TEMPORARY_MODE_EDITOR_MODE_ATTR,
            SONOFF_TRVZBT_TEMPORARY_MODE_EDITOR_DURATION_ATTR,
            SONOFF_TRVZBT_TEMPORARY_MODE_EDITOR_TARGET_TEMPERATURE_ATTR,
            SONOFF_TRVZBT_TEMPORARY_MODE_EDITOR_APPLY_STATUS_ATTR,
            *SONOFF_TRVZBT_SCHEDULE_ATTR_BY_DAY.values(),
            *SONOFF_TRVZBT_SCHEDULE_EDITOR_PERIOD_TIME_ATTRS.values(),
            *SONOFF_TRVZBT_SCHEDULE_EDITOR_PERIOD_TEMP_ATTRS.values(),
        }
        local_temperature_offset_name = self.AttributeDefs.local_temperature_offset.name

        success = {}
        remaining = []
        for attr in attributes:
            try:
                attr_def = self.find_attribute(attr)
            except KeyError:
                attr_def = None
            attrid = attr_def.id if attr_def is not None else attr
            if attrid in local_attr_ids:
                default = (
                    _sonoff_trvzbt_today_schedule_day()
                    if attrid == SONOFF_TRVZBT_SCHEDULE_EDITOR_DAY_ATTR
                    else SONOFF_TRVZBT_SCHEDULE_EDITOR_DEFAULTS.get(attrid)
                )
                value = self._attr_cache.get(attrid, default)
                if attrid == SONOFF_TRVZBT_SCHEDULE_EDITOR_DAY_ATTR:
                    try:
                        value = int(value)
                    except (TypeError, ValueError):
                        value = default
                    if value not in SONOFF_TRVZBT_SCHEDULE_DAY_LOOKUP:
                        value = default
                    self._update_attribute(attrid, value)
                success[attr_def.name if attr_def is not None else attrid] = value
            elif attrid == SONOFF_TRVZBT_LOCAL_TEMPERATURE_OFFSET_ATTR:
                thermostat_cluster = getattr(self.endpoint, "in_clusters", {}).get(
                    SonoffThermostat.cluster_id
                )
                if thermostat_cluster is None:
                    success[local_temperature_offset_name] = self._attr_cache.get(
                        attrid
                    )
                    continue

                real_attr_name = (
                    SonoffThermostat.AttributeDefs.local_temperature_calibration.name
                )
                real_success, _failure = await thermostat_cluster.read_attributes(
                    [real_attr_name],
                    allow_cache=allow_cache,
                    only_cache=only_cache,
                    manufacturer=manufacturer,
                )
                if real_attr_name in real_success:
                    self._update_attribute(attrid, real_success[real_attr_name])
                success[local_temperature_offset_name] = self._attr_cache.get(attrid)
            else:
                remaining.append(attr)

        failure = {}
        if remaining:
            real_success, failure = await super().read_attributes(
                remaining,
                allow_cache=allow_cache,
                only_cache=only_cache,
                manufacturer=manufacturer,
            )
            success.update(real_success)

        return success, failure

    async def write_attributes(self, attributes, manufacturer=None, **kwargs):  # noqa: C901
        """Handle local virtual attributes before forwarding real writes."""

        schedule_editor_attr_ids = {
            SONOFF_TRVZBT_SCHEDULE_EDITOR_GROUP_ATTR,
            SONOFF_TRVZBT_SCHEDULE_EDITOR_DAY_ATTR,
            SONOFF_TRVZBT_SCHEDULE_EDITOR_PERIOD_COUNT_ATTR,
            *SONOFF_TRVZBT_SCHEDULE_EDITOR_PERIOD_TIME_ATTRS.values(),
            *SONOFF_TRVZBT_SCHEDULE_EDITOR_PERIOD_TEMP_ATTRS.values(),
        }
        schedule_editor_attr_names = {
            self.AttributeDefs.schedule_editor_group.name,
            self.AttributeDefs.schedule_editor_day.name,
            self.AttributeDefs.schedule_editor_period_count.name,
            self.AttributeDefs.schedule_period_1_time.name,
            self.AttributeDefs.schedule_period_2_time.name,
            self.AttributeDefs.schedule_period_3_time.name,
            self.AttributeDefs.schedule_period_4_time.name,
            self.AttributeDefs.schedule_period_5_time.name,
            self.AttributeDefs.schedule_period_6_time.name,
            self.AttributeDefs.schedule_period_7_time.name,
            self.AttributeDefs.schedule_period_8_time.name,
            self.AttributeDefs.schedule_period_9_time.name,
            self.AttributeDefs.schedule_period_10_time.name,
            self.AttributeDefs.schedule_period_11_time.name,
            self.AttributeDefs.schedule_period_12_time.name,
            self.AttributeDefs.schedule_period_1_temperature.name,
            self.AttributeDefs.schedule_period_2_temperature.name,
            self.AttributeDefs.schedule_period_3_temperature.name,
            self.AttributeDefs.schedule_period_4_temperature.name,
            self.AttributeDefs.schedule_period_5_temperature.name,
            self.AttributeDefs.schedule_period_6_temperature.name,
            self.AttributeDefs.schedule_period_7_temperature.name,
            self.AttributeDefs.schedule_period_8_temperature.name,
            self.AttributeDefs.schedule_period_9_temperature.name,
            self.AttributeDefs.schedule_period_10_temperature.name,
            self.AttributeDefs.schedule_period_11_temperature.name,
            self.AttributeDefs.schedule_period_12_temperature.name,
        }
        temporary_mode_editor_attr_ids = {
            SONOFF_TRVZBT_TEMPORARY_MODE_EDITOR_MODE_ATTR,
            SONOFF_TRVZBT_TEMPORARY_MODE_EDITOR_DURATION_ATTR,
            SONOFF_TRVZBT_TEMPORARY_MODE_EDITOR_TARGET_TEMPERATURE_ATTR,
        }
        temporary_mode_editor_attr_names = {
            self.AttributeDefs.temporary_mode_editor_mode.name,
            self.AttributeDefs.temporary_mode_editor_duration.name,
            self.AttributeDefs.temporary_mode_editor_target_temperature.name,
        }
        temporary_mode_attr_name = self.AttributeDefs.temporary_mode.name
        temporary_mode_attr_id = self.AttributeDefs.temporary_mode.id
        temporary_duration_attr_name = self.AttributeDefs.temporary_mode_duration.name
        temporary_duration_attr_id = self.AttributeDefs.temporary_mode_duration.id
        local_temperature_offset_attr_name = (
            self.AttributeDefs.local_temperature_offset.name
        )
        local_temperature_offset_attr_id = (
            self.AttributeDefs.local_temperature_offset.id
        )

        remaining_attributes = dict(attributes)

        thermostat_cluster = getattr(self.endpoint, "in_clusters", {}).get(
            SonoffThermostat.cluster_id
        )
        for key in (
            local_temperature_offset_attr_name,
            local_temperature_offset_attr_id,
        ):
            if key in remaining_attributes:
                value = remaining_attributes.pop(key)
                if thermostat_cluster is None:
                    raise ValueError("thermostat cluster is not available")
                await thermostat_cluster.write_attributes(
                    {
                        SonoffThermostat.AttributeDefs.local_temperature_calibration.name: value
                    },
                    manufacturer=manufacturer,
                    **kwargs,
                )
                self._update_attribute(local_temperature_offset_attr_id, value)
                break

        for key in list(remaining_attributes):
            if key in schedule_editor_attr_names:
                attr = self.find_attribute(key)
                value = remaining_attributes.pop(key)
                validate_schedule_times = (
                    attr.id in SONOFF_TRVZBT_SCHEDULE_EDITOR_PERIOD_TIME_ATTRS.values()
                )
                if attr.id == SONOFF_TRVZBT_SCHEDULE_EDITOR_DAY_ATTR:
                    default_day = _sonoff_trvzbt_today_schedule_day()
                    try:
                        value = int(value)
                    except (TypeError, ValueError):
                        value = default_day
                    if value not in SONOFF_TRVZBT_SCHEDULE_DAY_LOOKUP:
                        value = default_day
                old_value = self._attr_cache.get(attr.id)
                self._update_attribute(attr.id, value)
                if validate_schedule_times:
                    try:
                        _sonoff_trvzbt_validate_schedule_times(self)
                    except ValueError:
                        self._update_attribute(attr.id, old_value)
                        raise
                if attr.id in (
                    SONOFF_TRVZBT_SCHEDULE_EDITOR_GROUP_ATTR,
                    SONOFF_TRVZBT_SCHEDULE_EDITOR_DAY_ATTR,
                ):
                    _sonoff_trvzbt_load_cached_schedule(self)
            elif key in schedule_editor_attr_ids:
                value = remaining_attributes.pop(key)
                validate_schedule_times = (
                    key in SONOFF_TRVZBT_SCHEDULE_EDITOR_PERIOD_TIME_ATTRS.values()
                )
                if key == SONOFF_TRVZBT_SCHEDULE_EDITOR_DAY_ATTR:
                    default_day = _sonoff_trvzbt_today_schedule_day()
                    try:
                        value = int(value)
                    except (TypeError, ValueError):
                        value = default_day
                    if value not in SONOFF_TRVZBT_SCHEDULE_DAY_LOOKUP:
                        value = default_day
                old_value = self._attr_cache.get(key)
                self._update_attribute(key, value)
                if validate_schedule_times:
                    try:
                        _sonoff_trvzbt_validate_schedule_times(self)
                    except ValueError:
                        self._update_attribute(key, old_value)
                        raise
                if key in (
                    SONOFF_TRVZBT_SCHEDULE_EDITOR_GROUP_ATTR,
                    SONOFF_TRVZBT_SCHEDULE_EDITOR_DAY_ATTR,
                ):
                    _sonoff_trvzbt_load_cached_schedule(self)

        for key in list(remaining_attributes):
            if key in temporary_mode_editor_attr_names:
                attr = self.find_attribute(key)
                value = remaining_attributes.pop(key)
                self._update_attribute(attr.id, value)
            elif key in temporary_mode_editor_attr_ids:
                value = remaining_attributes.pop(key)
                self._update_attribute(key, value)

        for key in (temporary_mode_attr_name, temporary_mode_attr_id):
            if key in remaining_attributes:
                value = remaining_attributes[key]
                if int(value) == int(SonoffTemporaryMode.None_):
                    remaining_attributes.pop(key)
                    self._update_attribute(
                        temporary_mode_attr_id, SonoffTemporaryMode.None_
                    )
                break

        written_temporary_mode = None
        for key in (temporary_mode_attr_name, temporary_mode_attr_id):
            if key in remaining_attributes:
                written_temporary_mode = remaining_attributes[key]
                break

        written_duration = None
        for key in (temporary_duration_attr_name, temporary_duration_attr_id):
            if key in remaining_attributes:
                written_duration = remaining_attributes[key]
                break

        target_temporary_mode = (
            written_temporary_mode
            if written_temporary_mode is not None
            else self._attr_cache.get(temporary_mode_attr_id)
        )
        target_duration = (
            written_duration
            if written_duration is not None
            else self._attr_cache.get(temporary_duration_attr_id)
        )

        if (
            (written_temporary_mode is not None or written_duration is not None)
            and target_temporary_mode is not None
            and target_duration is not None
        ):
            duration_seconds = int(target_duration)
            if duration_seconds < 0:
                raise ValueError("temporary_mode_duration must not be negative")
            if duration_seconds % 60 != 0:
                raise ValueError(
                    "temporary_mode_duration must be a whole number of minutes"
                )

            mode_value = int(target_temporary_mode)
            if mode_value == int(SonoffTemporaryMode.Boost):
                max_seconds = 180 * 60
                if duration_seconds > max_seconds:
                    raise ValueError(
                        "temporary_mode_duration must be 0-180 minutes "
                        "while Boost mode is active"
                    )
            elif mode_value == int(SonoffTemporaryMode.Timer):
                max_seconds = 1440 * 60
                if duration_seconds > max_seconds:
                    raise ValueError(
                        "temporary_mode_duration must be 0-1440 minutes "
                        "while Timer mode is active"
                    )

        if remaining_attributes:
            return await super().write_attributes(
                remaining_attributes, manufacturer=manufacturer, **kwargs
            )

        return ({}, {})

    def handle_cluster_request(self, hdr, args, *super_args, **kwargs):
        """Log decoded private schedule responses."""

        self._sonoff_trvzbt_schedule_temporary_mode_read(delay=5)
        self._sonoff_trvzbt_schedule_device_work_mode_read(delay=5)

        if hdr.command_id == 0x10:
            data = _sonoff_trvzbt_bytes(args)
            if len(data) >= 2:
                status_name = "success" if data[1] == 0x00 else "fail"
                self._update_attribute(
                    SONOFF_TRVZBT_BLUETOOTH_PAIRING_STATUS_ATTR, status_name
                )
                pending_request = getattr(
                    self,
                    "_sonoff_trvzbt_pending_bluetooth_pairing_request",
                    None,
                )
                if pending_request is None:
                    pending_request = (
                        SONOFF_TRVZBT_BLUETOOTH_PAIRING_REQUEST_BY_EVENT.get(data[0])
                    )
                if pending_request is not None:
                    self._sonoff_trvzbt_pending_bluetooth_pairing_request = None
                LOGGER.info(
                    "TRV-ZBT bluetooth pairing response: prefix=%s status=%s raw=%s",
                    data[0],
                    status_name,
                    data.hex(" "),
                )
                return None

        if hdr.command_id == 0x13:
            schedule = parse_sonoff_trvzbt_schedule_group(args)
            if schedule is None:
                LOGGER.debug(
                    "TRV-ZBT schedule group response: unable to decode %r", args
                )
            elif schedule["response_type"] == "write":
                self._update_attribute(
                    SONOFF_TRVZBT_SCHEDULE_STATUS_ATTR, schedule["status_name"]
                )
                LOGGER.info(
                    "TRV-ZBT schedule group write response: active=%s status=%s raw=%s",
                    schedule["active_num"],
                    schedule["status_name"],
                    schedule["raw"],
                )
            else:
                for day_bit, attrid in SONOFF_TRVZBT_SCHEDULE_ATTR_BY_DAY.items():
                    if schedule["day_of_week"] & day_bit:
                        self._update_attribute(attrid, schedule["schedule"])
                _sonoff_trvzbt_cache_schedule(self, schedule)
                _sonoff_trvzbt_update_editor_from_schedule(self, schedule)
                LOGGER.info(
                    "TRV-ZBT schedule group %s %s: active=%s transitions=%s "
                    "mode=0x%02x schedule=%s raw=%s",
                    schedule["day_name"],
                    f"0x{schedule['day_of_week']:02x}",
                    schedule["active_num"],
                    schedule["transition_count"],
                    schedule["mode"],
                    schedule["schedule"],
                    schedule["raw"],
                )

            return None

        return super().handle_cluster_request(hdr, args, *super_args, **kwargs)


SONOFF_TRVZBT_QUIRK_BUILDER = (
    QuirkBuilder("SONOFF", "TRV-ZBT")
    .replaces(SonoffBasicCluster)
    .replaces(SonoffThermostat)
    .replaces(CustomSonoffCluster)
    .prevent_default_entity_creation(function=_sonoff_trvzbt_is_replaced_default_entity)
    .enum(
        SonoffThermostat.AttributeDefs.system_mode.name,
        SonoffSystemMode,
        SonoffThermostat.cluster_id,
        translation_key="system_mode",
        fallback_name="System mode",
    )
    .number(
        SonoffThermostat.AttributeDefs.occupied_heating_setpoint.name,
        SonoffThermostat.cluster_id,
        min_value=5.0,
        max_value=30.0,
        step=0.5,
        device_class=NumberDeviceClass.TEMPERATURE,
        unit=UnitOfTemperature.CELSIUS,
        multiplier=0.01,
        translation_key="heating_target_temperature",
        fallback_name="Heating Target Temperature",
    )
    .number(
        CustomSonoffCluster.AttributeDefs.local_temperature_offset.name,
        CustomSonoffCluster.cluster_id,
        min_value=-10.0,
        max_value=10.0,
        step=0.2,
        device_class=NumberDeviceClass.TEMPERATURE,
        unit=UnitOfTemperature.CELSIUS,
        multiplier=0.1,
        translation_key="local_temperature_offset",
        fallback_name="Local temperature offset",
    )
    .switch(
        CustomSonoffCluster.AttributeDefs.temperature_control_mode.name,
        CustomSonoffCluster.cluster_id,
        on_value=2,
        off_value=1,
        translation_key="adaptive_mode",
        fallback_name="Adaptive mode",
    )
    .switch(
        CustomSonoffCluster.AttributeDefs.child_lock.name,
        CustomSonoffCluster.cluster_id,
        translation_key="child_lock",
        fallback_name="Child lock",
    )
    .switch(
        CustomSonoffCluster.AttributeDefs.open_window.name,
        CustomSonoffCluster.cluster_id,
        translation_key="open_window",
        fallback_name="Open window",
    )
    .number(
        CustomSonoffCluster.AttributeDefs.temporary_mode_editor_duration.name,
        CustomSonoffCluster.cluster_id,
        min_value=0,
        max_value=1440,
        step=1,
        device_class=NumberDeviceClass.DURATION,
        unit=UnitOfTime.MINUTES,
        multiplier=1 / 60,
        translation_key="temporary_mode_duration",
        fallback_name="Temporary mode duration",
    )
    .number(
        CustomSonoffCluster.AttributeDefs.temporary_mode_editor_target_temperature.name,
        CustomSonoffCluster.cluster_id,
        min_value=5.0,
        max_value=30.0,
        step=0.5,
        device_class=NumberDeviceClass.TEMPERATURE,
        unit=UnitOfTemperature.CELSIUS,
        multiplier=0.01,
        translation_key="timer_mode_target_temperature",
        fallback_name="Timer mode target temperature",
    )
    .enum(
        CustomSonoffCluster.AttributeDefs.temporary_mode_editor_mode.name,
        SonoffTemporaryModeEditor,
        CustomSonoffCluster.cluster_id,
        translation_key="temporary_mode",
        fallback_name="Temporary mode",
    )
    .command_button(
        "temporary_mode_apply",
        CustomSonoffCluster.cluster_id,
        unique_id_suffix="temporary_mode_apply",
        translation_key="temporary_mode_apply",
        fallback_name="Temporary mode apply",
    )
    .enum(
        CustomSonoffCluster.AttributeDefs.screen_direction.name,
        SonoffScreenDirection,
        CustomSonoffCluster.cluster_id,
        translation_key="screen_direction",
        fallback_name="Screen direction",
    )
    .enum(
        CustomSonoffCluster.AttributeDefs.low_battery_valve_state.name,
        SonoffLowBatteryValveState,
        CustomSonoffCluster.cluster_id,
        translation_key="low_battery_valve_state",
        fallback_name="Low battery valve state",
    )
    .number(
        CustomSonoffCluster.AttributeDefs.frost_protection_temperature.name,
        CustomSonoffCluster.cluster_id,
        min_value=5.0,
        max_value=15.0,
        step=0.5,
        device_class=NumberDeviceClass.TEMPERATURE,
        unit=UnitOfTemperature.CELSIUS,
        multiplier=0.01,
        translation_key="frost_protection_temperature",
        fallback_name="Frost protection temperature",
    )
    .number(
        CustomSonoffCluster.AttributeDefs.valve_opening_degree.name,
        CustomSonoffCluster.cluster_id,
        min_value=0,
        max_value=100,
        step=1,
        unit="%",
        entity_type=EntityType.CONFIG,
        translation_key="heating_valve_opening",
        fallback_name="Heating Valve Opening",
    )
    .number(
        CustomSonoffCluster.AttributeDefs.valve_closing_degree.name,
        CustomSonoffCluster.cluster_id,
        min_value=0,
        max_value=100,
        step=1,
        unit="%",
        entity_type=EntityType.CONFIG,
        translation_key="idle_valve_opening",
        fallback_name="Idle Valve Opening",
    )
    .number(
        CustomSonoffCluster.AttributeDefs.temperature_control_accuracy.name,
        CustomSonoffCluster.cluster_id,
        min_value=-1.0,
        max_value=-0.2,
        step=0.2,
        device_class=NumberDeviceClass.TEMPERATURE_DELTA,
        unit=UnitOfTemperature.CELSIUS,
        multiplier=0.01,
        translation_key="heating_on_offset",
        fallback_name="Heating ON Offset",
    )
    .switch(
        CustomSonoffCluster.AttributeDefs.temperature_sensor_select.name,
        CustomSonoffCluster.cluster_id,
        on_value=0x01,
        off_value=0x00,
        translation_key="temperature_sensor_select",
        fallback_name="External temperature sensor",
    )
    .number(
        CustomSonoffCluster.AttributeDefs.external_temperature_sensor_value.name,
        CustomSonoffCluster.cluster_id,
        min_value=-10.0,
        max_value=50.0,
        step=0.1,
        device_class=NumberDeviceClass.TEMPERATURE,
        unit=UnitOfTemperature.CELSIUS,
        multiplier=0.01,
        translation_key="external_temperature_sensor_value",
        fallback_name="External temperature sensor value",
    )
    .sensor(
        CustomSonoffCluster.AttributeDefs.fault_code.name,
        CustomSonoffCluster.cluster_id,
        attribute_converter=convert_sonoff_trvzbt_fault_code,
        translation_key="fault_status",
        fallback_name="Fault status",
    )
    .sensor(
        CustomSonoffCluster.AttributeDefs.device_work_mode.name,
        CustomSonoffCluster.cluster_id,
        attribute_converter=convert_sonoff_trvzbt_device_work_mode,
        translation_key="device_work_mode",
        fallback_name="Device work mode",
    )
    .sensor(
        CustomSonoffCluster.AttributeDefs.motor_travel_calibration_status.name,
        CustomSonoffCluster.cluster_id,
        attribute_converter=convert_sonoff_trvzbt_motor_travel_calibration_status,
        translation_key="motor_travel_calibration_status",
        fallback_name="Calibration status",
        entity_type=EntityType.DIAGNOSTIC,
    )
    .sensor(
        CustomSonoffCluster.AttributeDefs.hvac_message_notification.name,
        CustomSonoffCluster.cluster_id,
        attribute_converter=convert_sonoff_trvzbt_open_window_detected,
        translation_key="open_window_detected",
        fallback_name="Open window detected",
    )
    .command_button(
        "schedule_apply",
        CustomSonoffCluster.cluster_id,
        unique_id_suffix="schedule_apply",
        translation_key="schedule_apply",
        fallback_name="Schedule apply",
    )
    .command_button(
        "schedule_fetch",
        CustomSonoffCluster.cluster_id,
        unique_id_suffix="schedule_fetch",
        translation_key="schedule_fetch",
        fallback_name="Schedule fetch",
    )
    .command_button(
        "bluetooth_pairing_press",
        CustomSonoffCluster.cluster_id,
        unique_id_suffix="bluetooth_pairing",
        translation_key="bluetooth_pairing",
        fallback_name="Bluetooth pairing",
    )
    .enum(
        CustomSonoffCluster.AttributeDefs.schedule_editor_group.name,
        SonoffScheduleGroup,
        CustomSonoffCluster.cluster_id,
        translation_key="schedule_group",
        fallback_name="Schedule group",
    )
    .enum(
        CustomSonoffCluster.AttributeDefs.schedule_editor_day.name,
        SonoffScheduleDay,
        CustomSonoffCluster.cluster_id,
        translation_key="schedule_operating_day",
        fallback_name="Schedule operating day",
    )
)

for _index in range(1, SONOFF_TRVZBT_SCHEDULE_EDITOR_MAX_PERIODS + 1):
    SONOFF_TRVZBT_QUIRK_BUILDER = SONOFF_TRVZBT_QUIRK_BUILDER.enum(
        getattr(
            CustomSonoffCluster.AttributeDefs,
            f"schedule_period_{_index}_time",
        ).name,
        SonoffScheduleTime,
        CustomSonoffCluster.cluster_id,
        translation_key=f"schedule_period_{_index}_time",
        fallback_name=f"Schedule period {_index} start time",
    ).number(
        getattr(
            CustomSonoffCluster.AttributeDefs,
            f"schedule_period_{_index}_temperature",
        ).name,
        CustomSonoffCluster.cluster_id,
        min_value=5.0,
        max_value=30.0,
        step=0.5,
        device_class=NumberDeviceClass.TEMPERATURE,
        unit=UnitOfTemperature.CELSIUS,
        multiplier=0.01,
        translation_key=f"schedule_period_{_index}_temperature",
        fallback_name=f"Schedule period {_index} temperature",
    )

(
    SONOFF_TRVZBT_QUIRK_BUILDER.write_attr_button(
        attribute_name=CustomSonoffCluster.AttributeDefs.motor_travel_calibration.name,
        cluster_id=CustomSonoffCluster.cluster_id,
        attribute_value=0x01,
        unique_id_suffix="start_motor_travel_calibration",
        translation_key="calibrate_valve",
        fallback_name="Calibrate valve",
    ).add_to_registry()
)
