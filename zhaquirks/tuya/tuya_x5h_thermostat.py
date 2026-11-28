"""Tuya X5H wall thermostat (Beok TGR85-ZB, X5H-GB-B and clones), TS0601 _TZE200_2ekuz3dz.

Datapoints (as used by the Zigbee2MQTT x5h_thermostat converter):
  1 on/off, 2 program mode, 3 heating running, 7 sound, 10 frost protection,
  16 setpoint (0.1 C), 19 upper temperature (C), 24 local temperature (0.1 C),
  27 calibration (0.1 C), 30 schedule (raw), 31 week program, 39 factory reset,
  40 child lock, 43 sensor selection, 101 deadzone (0.1 C), 102 heating limit (C),
  104 backlight brightness.

Device specific behaviour handled here:
  * The setpoint is sent in 0.1 C units, but the thermostat only knows 0.5 C steps. Writes are
    rounded to the nearest 0.5 C, otherwise the device buttons move from e.g. 21.4 to 20.9.
  * Clock: the firmware reads only the first (UTC) field of the Tuya time reply and adds a fixed
    8 hours to it, without wrapping the day (Koenkk/zigbee2mqtt#14037). The reply therefore
    carries local time minus 8 hours, and no time is sent between 00:00 and 07:59 local time,
    when the display would show 24:00 to 31:59. The device asks for the time only after power
    up, so the time is also pushed on device traffic, at most once an hour.
  * Schedule (DP 30): 8 periods of hour, minute and temperature x10 (2 bytes, big endian). It is
    exposed as the text attribute "schedule" in the Zigbee2MQTT format
    "06:00/20.5 08:00/15 ... (8 periods)" and shown as a sensor. It can be written with
    the zha.set_zigbee_cluster_attribute action. The device does not report it on its own.
  * The generic thermostat sensors pi_heating_demand, setpoint_change_source and
    setpoint_change_source_timestamp are not created, the device has no such datapoints.
"""

import datetime
import math
import time
from typing import Any

from zigpy.profiles import zha
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.hvac import RunningState, Thermostat

from zhaquirks.builder import EntityType, UnitOfTemperature
from zhaquirks.tuya import (
    TUYA_SET_TIME,
    TuyaCommand,
    TuyaData,
    TuyaDatapointData,
    TuyaTimePayload,
)
from zhaquirks.tuya.builder import TuyaQuirkBuilder, TuyaTemperatureMeasurement
from zhaquirks.tuya.mcu import DPToAttributeMapping, TuyaMCUCluster
from zhaquirks.tuya.tuya_trv import TuyaThermostatV2

SCHEDULE_DP = 30
SCHEDULE_PERIODS = 8
SETPOINT_STEP = 50  # 0.5 C in the centidegrees of the ZCL thermostat cluster
FIRMWARE_TIME_OFFSET = 8 * 3600  # added by the firmware to the time it receives
NO_TIME_SYNC_BEFORE_HOUR = 8
TIME_PUSH_INTERVAL = 3600


class X5HProgramMode(t.enum8):
    """Program mode."""

    Manual = 0x00
    Program = 0x01


class X5HSensorSelection(t.enum8):
    """Sensor used for regulation."""

    Internal = 0x00
    External = 0x01
    Both = 0x02


class X5HBrightness(t.enum8):
    """Backlight brightness."""

    Off = 0x00
    Low = 0x01
    Medium = 0x02
    High = 0x03


class X5HWeekProgram(t.enum8):
    """Working days and rest days of the schedule."""

    Days_5_2 = 0x00
    Days_6_1 = 0x01
    Days_7 = 0x02


class RawBytes(bytes):
    """Bytes sent as a Tuya RAW datapoint as they are."""

    def serialize(self) -> bytes:
        """Serialize."""
        return bytes(self)


def schedule_from_raw(raw: bytes) -> str:
    """Convert the raw DP 30 value to the text format, '06:00/20.5 08:00/15 ...'."""
    raw = bytes(raw)
    periods = []
    for i in range(min(SCHEDULE_PERIODS, len(raw) // 4)):
        hour, minute, temp_hi, temp_lo = raw[4 * i : 4 * i + 4]
        temperature = ((temp_hi << 8) | temp_lo) / 10
        periods.append(f"{hour:02d}:{minute:02d}/{temperature:g}")
    return " ".join(periods)


def schedule_to_raw(text: str) -> RawBytes:
    """Convert the text format to the raw DP 30 value, raises ValueError when invalid."""
    periods = str(text).split()
    if len(periods) != SCHEDULE_PERIODS:
        raise ValueError(
            f"Schedule needs {SCHEDULE_PERIODS} periods, got {len(periods)}"
        )
    out = bytearray()
    for period in periods:
        time_part, temp_part = period.split("/")
        hour, minute = (int(x) for x in time_part.split(":", 1))
        temperature = float(temp_part)
        if not (0 <= hour < 24 and 0 <= minute < 60):
            raise ValueError(f"Invalid time {time_part}")
        if not (5 <= temperature <= 60) or (temperature * 2) % 1:
            raise ValueError(
                f"Invalid temperature {temp_part}, allowed 5 to 60 in steps of 0.5"
            )
        value = round(temperature * 10)
        out += bytes([hour, minute, value >> 8, value & 0xFF])
    return RawBytes(out)


def setpoint_to_dp(centidegrees: int) -> int:
    """Round a setpoint to the nearest 0.5 C (halves up) and convert it to 0.1 C."""
    return math.floor(centidegrees / SETPOINT_STEP + 0.5) * SETPOINT_STEP // 10


def signed16(value: int) -> int:
    """Local temperature is a signed 16 bit value inside the 32 bit datapoint."""
    if value & (1 << 15) and value < (1 << 16):
        return value - (1 << 16)
    return value


class X5HManufCluster(TuyaMCUCluster):
    """Tuya MCU cluster with the X5H clock compensation and the raw schedule write."""

    _last_time_sync: float = 0.0

    def send_time(self) -> bool:
        """Send the compensated local time, returns False when skipped."""
        now = datetime.datetime.now()
        if now.hour < NO_TIME_SYNC_BEFORE_HOUR:
            self.debug("X5H time sync skipped before %02d:00", NO_TIME_SYNC_BEFORE_HOUR)
            return False
        local = int((now - datetime.datetime(1970, 1, 1)).total_seconds())
        stamp = local - FIRMWARE_TIME_OFFSET
        payload = TuyaTimePayload()
        payload.extend(stamp.to_bytes(4, "big", signed=False))
        payload.extend(stamp.to_bytes(4, "big", signed=False))
        self._last_time_sync = time.monotonic()
        self.create_catching_task(
            super(TuyaMCUCluster, self).command(
                TUYA_SET_TIME, payload, expect_reply=False
            )
        )
        return True

    def handle_set_time_request(self, payload: t.uint16_t) -> foundation.Status:
        """Answer the time request with the compensated time."""
        self.send_time()
        return foundation.Status.SUCCESS

    def handle_cluster_request(
        self,
        hdr: foundation.ZCLHeader,
        args: list[Any],
        *,
        dst_addressing: t.AddrMode | None = None,
    ) -> None:
        """Handle the request, then push the time if the last sync is older than an hour."""
        super().handle_cluster_request(hdr, args, dst_addressing=dst_addressing)
        if hdr.command_id != TUYA_SET_TIME and (
            not self._last_time_sync
            or time.monotonic() - self._last_time_sync > TIME_PUSH_INTERVAL
        ):
            self.send_time()

    async def write_attributes(
        self, attributes: dict[str | int, Any], *args, **kwargs
    ) -> list:
        """Send the schedule as the raw DP 30, the generic MCU write carries numbers only."""
        schedule = None
        others = {}
        for key, value in attributes.items():
            if self.find_attribute(key).name == "schedule":
                schedule = value
            else:
                others[key] = value

        result = [[foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)]]
        if schedule is not None:
            raw = schedule_to_raw(schedule)
            command = TuyaCommand(
                status=0,
                tsn=self.endpoint.device.application.get_sequence(),
                datapoints=[TuyaDatapointData(SCHEDULE_DP, TuyaData(raw))],
            )
            await self.command(self.mcu_write_command, command, expect_reply=False)
            self.update_attribute("schedule", schedule_from_raw(raw))
        if others:
            result = await super().write_attributes(others, *args, **kwargs)
        return result


class X5HThermostat(TuyaThermostatV2):
    """Thermostat cluster with the X5H setpoint range (5 to 60 C)."""

    _CONSTANT_ATTRIBUTES = {
        **TuyaThermostatV2._CONSTANT_ATTRIBUTES,
        Thermostat.AttributeDefs.abs_min_heat_setpoint_limit.id: 500,
        Thermostat.AttributeDefs.abs_max_heat_setpoint_limit.id: 6000,
        Thermostat.AttributeDefs.min_heat_setpoint_limit.id: 500,
        Thermostat.AttributeDefs.max_heat_setpoint_limit.id: 6000,
    }


(
    TuyaQuirkBuilder("_TZE200_2ekuz3dz", "TS0601")
    .replaces_endpoint(1, device_type=zha.DeviceType.THERMOSTAT)
    .tuya_dp(
        dp_id=1,
        ep_attribute=X5HThermostat.ep_attribute,
        attribute_name=X5HThermostat.AttributeDefs.system_mode.name,
        converter=lambda x: (
            Thermostat.SystemMode.Heat if x else Thermostat.SystemMode.Off
        ),
        dp_converter=lambda x: x == Thermostat.SystemMode.Heat,
    )
    .tuya_dp(
        dp_id=3,
        ep_attribute=X5HThermostat.ep_attribute,
        attribute_name=X5HThermostat.AttributeDefs.running_state.name,
        converter=lambda x: RunningState.Heat_State_On if x else RunningState.Idle,
    )
    .tuya_dp(
        dp_id=16,
        ep_attribute=X5HThermostat.ep_attribute,
        attribute_name=X5HThermostat.AttributeDefs.occupied_heating_setpoint.name,
        converter=lambda x: x * 10,
        dp_converter=setpoint_to_dp,
    )
    .tuya_dp_multi(
        dp_id=24,
        attribute_mapping=[
            DPToAttributeMapping(
                X5HThermostat.ep_attribute,
                X5HThermostat.AttributeDefs.local_temperature.name,
                converter=lambda x: signed16(x) * 10,
            ),
            DPToAttributeMapping(
                TuyaTemperatureMeasurement.ep_attribute,
                TuyaTemperatureMeasurement.AttributeDefs.measured_value.name,
                converter=lambda x: signed16(x) * 10,
            ),
        ],
    )
    .adds(TuyaTemperatureMeasurement)
    .tuya_number(
        dp_id=27,
        type=t.int32s,
        attribute_name="local_temperature_calibration",
        min_value=-9.9,
        max_value=9.9,
        step=0.1,
        multiplier=0.1,
        unit=UnitOfTemperature.CELSIUS,
        translation_key="local_temperature_calibration",
        fallback_name="Local temperature calibration",
    )
    .tuya_number(
        dp_id=101,
        type=t.uint32_t,
        attribute_name="deadzone_temperature",
        min_value=0.5,
        max_value=9.5,
        step=0.5,
        multiplier=0.1,
        unit=UnitOfTemperature.CELSIUS,
        translation_key="deadzone_temperature",
        fallback_name="Deadzone temperature",
    )
    .tuya_number(
        dp_id=102,
        type=t.uint32_t,
        attribute_name="heating_temp_limit",
        min_value=5,
        max_value=60,
        step=1,
        unit=UnitOfTemperature.CELSIUS,
        translation_key="max_temperature",
        fallback_name="Max temperature",
    )
    .tuya_number(
        dp_id=19,
        type=t.uint32_t,
        attribute_name="upper_temp",
        min_value=35,
        max_value=95,
        step=1,
        unit=UnitOfTemperature.CELSIUS,
        translation_key="upper_temp",
        fallback_name="Upper temperature",
    )
    .tuya_enum(
        dp_id=2,
        attribute_name="preset_mode",
        enum_class=X5HProgramMode,
        translation_key="preset_mode",
        fallback_name="Preset mode",
    )
    .tuya_enum(
        dp_id=43,
        attribute_name="sensor_selection",
        enum_class=X5HSensorSelection,
        translation_key="local_temperature_source",
        fallback_name="Local temperature source",
    )
    .tuya_enum(
        dp_id=104,
        attribute_name="backlight_brightness",
        enum_class=X5HBrightness,
        translation_key="display_brightness",
        fallback_name="Display brightness",
    )
    .tuya_enum(
        dp_id=31,
        attribute_name="week",
        enum_class=X5HWeekProgram,
        translation_key="week_program",
        fallback_name="Week program",
    )
    .tuya_dp_attribute(
        dp_id=SCHEDULE_DP,
        attribute_name="schedule",
        type=t.CharacterString,
        access=foundation.ZCLAttributeAccess.Read | foundation.ZCLAttributeAccess.Write,
        converter=schedule_from_raw,
        dp_converter=schedule_to_raw,
    )
    .sensor(
        "schedule",
        X5HManufCluster.cluster_id,
        attribute_converter=str,
        entity_type=EntityType.DIAGNOSTIC,
        translation_key="schedule",
        fallback_name="Schedule",
    )
    .tuya_dp_attribute(
        dp_id=39,
        attribute_name="factory_reset",
        type=t.Bool,
        access=foundation.ZCLAttributeAccess.Write,
        converter=bool,
        dp_converter=bool,
    )
    .write_attr_button(
        "factory_reset",
        1,
        X5HManufCluster.cluster_id,
        translation_key="factory_reset",
        fallback_name="Factory reset",
    )
    .tuya_switch(
        dp_id=40,
        attribute_name="child_lock",
        translation_key="child_lock",
        fallback_name="Child lock",
    )
    .tuya_switch(
        dp_id=10,
        attribute_name="frost_protection",
        translation_key="frost_protection",
        fallback_name="Frost protection",
    )
    .tuya_switch(
        dp_id=7,
        attribute_name="sound",
        translation_key="sound_enabled",
        fallback_name="Sound enabled",
    )
    .prevent_default_entity_creation(
        endpoint_id=1,
        cluster_id=Thermostat.cluster_id,
        unique_id_suffix="pi_heating_demand",
    )
    .prevent_default_entity_creation(
        endpoint_id=1,
        cluster_id=Thermostat.cluster_id,
        unique_id_suffix="setpoint_change_source",
    )
    .prevent_default_entity_creation(
        endpoint_id=1,
        cluster_id=Thermostat.cluster_id,
        unique_id_suffix="setpoint_change_source_timestamp",
    )
    .adds(X5HThermostat)
    .skip_configuration()
    .add_to_registry(replacement_cluster=X5HManufCluster)
)
