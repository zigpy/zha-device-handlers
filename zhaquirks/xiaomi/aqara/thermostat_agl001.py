"""Aqara E1 Radiator Thermostat Quirk."""

from __future__ import annotations

from functools import reduce
import math
import struct
from typing import Any

from zigpy.profiles import zha
from zigpy.quirks import CustomCluster
import zigpy.types as t
from zigpy.zcl.clusters.general import Basic, Identify, Ota, Time
from zigpy.zcl.clusters.hvac import Thermostat

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.xiaomi import (
    LUMI,
    XiaomiAqaraE1Cluster,
    XiaomiCustomDevice,
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


class AqaraThermostatSpecificCluster(XiaomiAqaraE1Cluster):
    """Aqara manufacturer specific settings."""

    attributes = XiaomiAqaraE1Cluster.attributes.copy()
    attributes.update(
        {
            SYSTEM_MODE: ("system_mode", t.uint8_t, True),
            PRESET: ("preset", t.uint8_t, True),
            WINDOW_DETECTION: ("window_detection", t.uint8_t, True),
            VALVE_DETECTION: ("valve_detection", t.uint8_t, True),
            VALVE_ALARM: ("valve_alarm", t.uint8_t, True),
            CHILD_LOCK: ("child_lock", t.uint8_t, True),
            AWAY_PRESET_TEMPERATURE: ("away_preset_temperature", t.uint32_t, True),
            WINDOW_OPEN: ("window_open", t.uint8_t, True),
            CALIBRATED: ("calibrated", t.uint8_t, True),
            SCHEDULE: ("schedule", t.uint8_t, True),
            SCHEDULE_SETTINGS: ("schedule_settings", ScheduleSettings, True),
            SENSOR: ("sensor", t.uint8_t, True),
            BATTERY_PERCENTAGE: ("battery_percentage", t.uint8_t, True),
        }
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
        super()._update_attribute(attrid, value)


class AGL001(XiaomiCustomDevice):
    """Aqara E1 Radiator Thermostat (AGL001) Device."""

    signature = {
        # <SimpleDescriptor endpoint=1 profile=260 device_type=769
        # device_version=1
        # input_clusters=[0, 1, 3, 513, 64704]
        # output_clusters=[3, 513, 64704]>
        MODELS_INFO: [(LUMI, "lumi.airrtc.agl001")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.THERMOSTAT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Thermostat.cluster_id,
                    Time.cluster_id,
                    XiaomiPowerConfiguration.cluster_id,
                    AqaraThermostatSpecificCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Thermostat.cluster_id,
                    AqaraThermostatSpecificCluster.cluster_id,
                ],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    ThermostatCluster,
                    Time.cluster_id,
                    XiaomiPowerConfiguration,
                    AqaraThermostatSpecificCluster,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    ThermostatCluster,
                    AqaraThermostatSpecificCluster,
                    Ota.cluster_id,
                ],
            }
        }
    }
