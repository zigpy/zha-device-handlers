"""Aqara E1 Radiator Thermostat Quirk."""

from __future__ import annotations

from functools import reduce
import math
import struct
import time
from typing import Any, Final

from zigpy.profiles import zha
from zigpy.quirks import CustomCluster
import zigpy.types as t
from zigpy.zcl.clusters.general import Basic, Identify, Ota, Time
from zigpy.zcl.clusters.hvac import Thermostat
from zigpy.zcl.foundation import ZCLAttributeDef

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


class Constants:
    """Constants specific for Aqara E1 TRV.

    This class contains protocol-specific byte sequences for the Aqara E1 radiator
    thermostat. The values define the structure of proprietary commands used to
    configure internal/external temperature sensor switching and temperature settings.
    """

    SENSOR_ID = bytes.fromhex("00158d00019d1b98")
    SENSOR_ID_SUFFIX = bytes([0x00, 0x01, 0x00, 0x55])
    INTERNAL_SENSOR_ACTION_CODES = [bytes([0x3D, 0x05]), bytes([0x3D, 0x04])]
    EXTERNAL_SENSOR_ACTION_CODES = [bytes([0x3D, 0x04]), bytes([0x3D, 0x05])]
    INTERNAL_SENSOR_PADDING = bytes(12)
    EXTERNAL_SENSOR_DATA_BLOCK_1 = bytes(
        [0x13, 0x0A, 0x02, 0x00, 0x00, 0x64, 0x04, 0xCE, 0xC2, 0xB6, 0xC8]
    )
    EXTERNAL_SENSOR_DATA_BLOCK_2 = bytes(
        [
            0x16,
            0x0A,
            0x02,
            0x0A,
            0xC9,
            0xE8,
            0xB1,
            0xB8,
            0xD4,
            0xDA,
            0xCF,
            0xDF,
            0xC0,
            0xEB,
        ]
    )
    EXTERNAL_SENSOR_TRAILING_1 = bytes([0x00, 0x00, 0x00, 0x00, 0x00, 0x01, 0x3D])
    EXTERNAL_SENSOR_TRAILING_2 = bytes([0x64])
    EXTERNAL_SENSOR_TRAILING_3 = bytes([0x65])
    EXTERNAL_SENSOR_PARAMS2_SUFFIX = bytes([0x08, 0x00, 0x07, 0xFD])
    EXTERNAL_SENSOR_TRAILING_4 = bytes([0x04])
    # Action codes for aqara_header method
    ACTION_SET_EXTERNAL_TEMP = 0x05
    ACTION_SET_INTERNAL_SENSOR = 0x04
    ACTION_SET_EXTERNAL_SENSOR = 0x02
    # Header action/command identifiers
    HEADER_ACTION_SENSOR_TEMP = 0x12
    HEADER_ACTION_SENSOR_MODE = 0x13


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
        if (
            ZCL_SYSTEM_MODE in attributes
            or AqaraThermostatSpecificCluster.AttributeDefs.system_mode.name
            in attributes
        ):
            self.debug("Passing 'system_mode' read to Xiaomi cluster")

            if ZCL_SYSTEM_MODE in attributes:
                remaining_attributes.remove(ZCL_SYSTEM_MODE)
            if (
                AqaraThermostatSpecificCluster.AttributeDefs.system_mode.name
                in attributes
            ):
                remaining_attributes.remove(
                    AqaraThermostatSpecificCluster.AttributeDefs.system_mode.name
                )

            successful_r, failed_r = await self.endpoint.opple_cluster.read_attributes(
                [AqaraThermostatSpecificCluster.AttributeDefs.system_mode.id],
                allow_cache,
                only_cache,
                manufacturer,
            )
            # convert Xiaomi system_mode to ZCL attribute
            if (
                AqaraThermostatSpecificCluster.AttributeDefs.system_mode.id
                in successful_r
            ):
                successful_r[ZCL_SYSTEM_MODE] = XIAOMI_SYSTEM_MODE_MAP[
                    successful_r.pop(
                        AqaraThermostatSpecificCluster.AttributeDefs.system_mode.id
                    )
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
        if AqaraThermostatSpecificCluster.AttributeDefs.system_mode.name in attributes:
            remaining_attributes.pop(
                AqaraThermostatSpecificCluster.AttributeDefs.system_mode.name
            )
            system_mode_value = attributes.get(
                AqaraThermostatSpecificCluster.AttributeDefs.system_mode.name
            )

        # write system_mode to Xiaomi cluster if applicable
        if system_mode_value is not None:
            self.debug("Passing 'system_mode' write to Xiaomi cluster")
            result += await self.endpoint.opple_cluster.write_attributes(
                {
                    AqaraThermostatSpecificCluster.AttributeDefs.system_mode.id: min(
                        int(system_mode_value), 1
                    )
                }
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

    class AttributeDefs(XiaomiAqaraE1Cluster.AttributeDefs):
        """Attribute definitions."""

        system_mode: Final = ZCLAttributeDef(
            id=0x0271, type=t.uint8_t, is_manufacturer_specific=True
        )
        preset: Final = ZCLAttributeDef(
            id=0x0272, type=t.uint8_t, is_manufacturer_specific=True
        )
        window_detection: Final = ZCLAttributeDef(
            id=0x0273, type=t.uint8_t, is_manufacturer_specific=True
        )
        valve_detection: Final = ZCLAttributeDef(
            id=0x0274, type=t.uint8_t, is_manufacturer_specific=True
        )
        valve_alarm: Final = ZCLAttributeDef(
            id=0x0275, type=t.uint8_t, is_manufacturer_specific=True
        )
        schedule_settings: Final = ZCLAttributeDef(
            id=0x0276, type=ScheduleSettings, is_manufacturer_specific=True
        )
        child_lock: Final = ZCLAttributeDef(
            id=0x0277, type=t.uint8_t, is_manufacturer_specific=True
        )
        away_preset_temperature: Final = ZCLAttributeDef(
            id=0x0279, type=t.uint32_t, is_manufacturer_specific=True
        )
        window_open: Final = ZCLAttributeDef(
            id=0x027A, type=t.uint8_t, is_manufacturer_specific=True
        )
        calibrated: Final = ZCLAttributeDef(
            id=0x027B, type=t.uint8_t, is_manufacturer_specific=True
        )
        schedule: Final = ZCLAttributeDef(
            id=0x027D, type=t.uint8_t, is_manufacturer_specific=True
        )
        sensor: Final = ZCLAttributeDef(
            id=0x027E, type=t.uint8_t, is_manufacturer_specific=True
        )
        battery_percentage: Final = ZCLAttributeDef(
            id=0x040A, type=t.uint8_t, is_manufacturer_specific=True
        )
        sensor_temp: Final = (
            ZCLAttributeDef(  # Fake address to pass external sensor temperature
                id=0x1392, type=t.uint32_t, is_manufacturer_specific=True
            )
        )
        sensor_attr: Final = ZCLAttributeDef(
            id=0xFFF2, type=t.LVBytes, is_manufacturer_specific=True
        )

    def _update_attribute(self, attrid, value):
        self.debug("Updating attribute on Xiaomi cluster %s with %s", attrid, value)
        if attrid == self.AttributeDefs.battery_percentage.id:
            self.endpoint.power.battery_percent_reported(value)
        elif attrid == self.AttributeDefs.system_mode.id:
            # update ZCL system_mode attribute (e.g. on attribute reports)
            self.endpoint.thermostat.update_attribute(
                ZCL_SYSTEM_MODE, XIAOMI_SYSTEM_MODE_MAP[value]
            )
        super()._update_attribute(attrid, value)

    def aqara_header(self, counter: int, params: bytes, action: int) -> bytes:
        """Build Aqara vendor-specific frame header.

        This helper wraps an already constructed ``params`` payload with the
        manufacturer header used by the E1 radiator thermostat when sending
        proprietary commands (for example, switching between internal and
        external temperature sensors).

        Args:
            counter: One-byte message sequence counter that is included in
                the header and typically echoed by the device.
            params: Vendor-specific payload that will follow the header. The
                length of this byte array is encoded into the header.
            action: One-byte Aqara action/command code that selects which
                proprietary action the payload performs. The caller uses
                values such as ACTION_SET_EXTERNAL_TEMP, ACTION_SET_INTERNAL_SENSOR,
                and ACTION_SET_EXTERNAL_SENSOR.

        Returns:
            The complete header bytes to prepend to ``params`` before sending
            the command to the device.

        """
        header = bytes([0xAA, 0x71, len(params) + 3, 0x44, counter])
        integrity = (512 - sum(header)) % 256

        return header + bytes([integrity, action, 0x41, len(params)])

    @staticmethod
    def _float_to_hex(f: float) -> str:
        """Convert float to hex string representation."""
        return hex(struct.unpack("<I", struct.pack("<f", f))[0])

    @staticmethod
    def _build_sensor_mode_params(
        is_external: bool, device: bytes, timestamp: bytes
    ) -> tuple[bytes, bytes]:
        """Build params1 and params2 for internal/external sensor mode switching.

        This method constructs the two parameter payloads needed to configure the device
        to use either the internal temperature sensor or an external one. The two payloads
        (params1 and params2) are sent in separate aqara_header commands to complete the
        sensor mode switch.

        Args:
            is_external: True to switch to external sensor mode, False for internal.
            device: The device's IEEE address as bytes for inclusion in the command payload.
            timestamp: The current Unix timestamp as bytes (in reverse byte order) to include
                in the command.

        Returns:
            A tuple of (params1, params2) where each is a bytes object representing the
            complete parameter payload for one of the two configuration commands.

        """
        if is_external:
            # External sensor
            # params1
            p1 = (
                timestamp
                + Constants.EXTERNAL_SENSOR_ACTION_CODES[0]
                + device
                + Constants.SENSOR_ID
            )
            p1 += Constants.SENSOR_ID_SUFFIX
            p1 += Constants.EXTERNAL_SENSOR_DATA_BLOCK_1
            p1 += Constants.EXTERNAL_SENSOR_TRAILING_1
            p1 += Constants.EXTERNAL_SENSOR_TRAILING_2
            p1 += Constants.EXTERNAL_SENSOR_TRAILING_3
            # params2
            p2 = (
                timestamp
                + Constants.EXTERNAL_SENSOR_ACTION_CODES[1]
                + device
                + Constants.SENSOR_ID
            )
            p2 += Constants.EXTERNAL_SENSOR_PARAMS2_SUFFIX
            p2 += Constants.EXTERNAL_SENSOR_DATA_BLOCK_2
            p2 += Constants.EXTERNAL_SENSOR_TRAILING_1
            p2 += Constants.EXTERNAL_SENSOR_TRAILING_4
            p2 += Constants.EXTERNAL_SENSOR_TRAILING_3
        else:
            # Internal sensor
            # params1
            p1 = (
                timestamp
                + Constants.INTERNAL_SENSOR_ACTION_CODES[0]
                + device
                + Constants.INTERNAL_SENSOR_PADDING
            )
            # params2
            p2 = (
                timestamp
                + Constants.INTERNAL_SENSOR_ACTION_CODES[1]
                + device
                + Constants.INTERNAL_SENSOR_PADDING
            )
        return p1, p2

    async def write_attributes(
        self, attributes: dict[str | int, Any], manufacturer: int | None = None
    ) -> list:
        """Write attributes to device with internal 'attributes' validation."""
        attrs: dict[str | int, Any] = {}

        for attr, value in attributes.items():
            # implemented with help from https://github.com/Koenkk/zigbee-herdsman-converters/blob/master/devices/xiaomi.js
            attr_def = self.find_attribute(attr)

            if attr_def and attr_def.id == self.AttributeDefs.sensor_temp.id:
                # set external sensor temperature; value is expected in degrees Celsius (e.g. 25.0 for 25°C)
                temperature_buf = bytearray.fromhex(
                    self._float_to_hex(round(float(value)))[2:]
                )

                params = bytearray(Constants.SENSOR_ID)
                params += Constants.SENSOR_ID_SUFFIX
                params += temperature_buf

                attrs[self.AttributeDefs.sensor_attr.name] = self.aqara_header(
                    Constants.HEADER_ACTION_SENSOR_TEMP,
                    bytes(params),
                    Constants.ACTION_SET_EXTERNAL_TEMP,
                ) + bytes(params)

            elif attr_def and attr_def.id == self.AttributeDefs.sensor.id:
                # set internal/external temperature sensor
                device = bytearray.fromhex(
                    f"{self.endpoint.device.ieee}".replace(":", "")
                )

                timestamp = bytes(reversed(t.uint32_t(int(time.time())).serialize()))

                is_external = bool(value)
                params1, params2 = self._build_sensor_mode_params(
                    is_external, device, timestamp
                )

                attrs1 = {}
                attrs1[self.AttributeDefs.sensor_attr.name] = (
                    self.aqara_header(
                        Constants.HEADER_ACTION_SENSOR_TEMP,
                        params1,
                        Constants.ACTION_SET_EXTERNAL_SENSOR
                        if is_external
                        else Constants.ACTION_SET_INTERNAL_SENSOR,
                    )
                    + params1
                )
                attrs[self.AttributeDefs.sensor_attr.name] = (
                    self.aqara_header(
                        Constants.HEADER_ACTION_SENSOR_MODE,
                        params2,
                        Constants.ACTION_SET_EXTERNAL_SENSOR
                        if is_external
                        else Constants.ACTION_SET_INTERNAL_SENSOR,
                    )
                    + params2
                )

                await super().write_attributes(attrs1, manufacturer)
            else:
                self.debug(
                    "Passing through attribute %r (value: %r) to base implementation; not handled by Aqara quirk.",
                    attr,
                    value,
                )
                attrs[attr] = value

        result = await super().write_attributes(attrs, manufacturer)
        return result


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
