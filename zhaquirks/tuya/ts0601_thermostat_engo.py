"""ENGO EONE-230B/W Zigbee Smart Thermostat quirk.

References:
    - Z2M: https://github.com/Koenkk/zigbee-herdsman-converters/blob/master/src/devices/engo.ts
    - Device: https://www.zigbee2mqtt.io/devices/EONE-230W.html
    - Product: https://engocontrols.com/en/produkt/eone-230b-3/

"""

from typing import Any

from zigpy.quirks.v2 import EntityType
from zigpy.quirks.v2.homeassistant import PERCENTAGE, UnitOfTemperature
from zigpy.quirks.v2.homeassistant.sensor import SensorDeviceClass, SensorStateClass
from zigpy.types import t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.hvac import Thermostat

from zhaquirks.tuya import TUYA_SET_TIME, TuyaTimePayload
from zhaquirks.tuya.builder import TuyaQuirkBuilder
from zhaquirks.tuya.mcu import TuyaMCUCluster


def parse_schedule(data: bytes) -> str:
    """Parse binary schedule data to Z2M-compatible string format.

    Binary format:
    - Byte 0: Day number (1=Mon, 7=Sun)
    - Byte 1: Transition count (typically 6)
    - Then for each transition (4 bytes):
      - Byte 0: Hour (0-23)
      - Byte 1: Minute (0-59)
      - Byte 2-3: Temperature × 10 (big-endian)

    Output format: "HH:MM/TEMP HH:MM/TEMP ..." (e.g., "06:00/21.0 08:00/18.0")
    """
    if not data or len(data) < 2:
        return ""

    transition_count = data[1]
    if len(data) < 2 + transition_count * 4:
        return ""

    schedule_parts = []
    for i in range(transition_count):
        offset = 2 + i * 4
        hour = data[offset]
        minute = data[offset + 1]
        temp_raw = (data[offset + 2] << 8) | data[offset + 3]
        temp = temp_raw / 10.0
        schedule_parts.append(f"{hour:02d}:{minute:02d}/{temp:.1f}")

    return " ".join(schedule_parts)


def format_schedule(schedule_str: str, day_num: int) -> bytes:
    """Convert Z2M-compatible schedule string to binary format.

    Input format: "HH:MM/TEMP HH:MM/TEMP ..." (e.g., "06:00/21.0 08:00/18.0")
    """
    if not schedule_str:
        return b""

    parts = schedule_str.strip().split()
    result = bytearray([day_num, len(parts)])

    for part in parts:
        time_temp = part.split("/")
        if len(time_temp) != 2:
            continue
        hour_min = time_temp[0].split(":")
        hour = int(hour_min[0])
        minute = int(hour_min[1])
        temp = int(float(time_temp[1]) * 10)
        result.extend([hour, minute, (temp >> 8) & 0xFF, temp & 0xFF])

    return bytes(result)


class SystemMode(t.enum8):
    """System mode: heating or cooling."""

    Heat = 0x00
    Cool = 0x01


class PresetMode(t.enum8):
    """Operating preset modes."""

    Manual = 0x00
    Program = 0x01
    Holiday = 0x02
    Temporary = 0x03
    Away = 0x04
    Frost = 0x05


class SensorSelect(t.enum8):
    """Temperature sensor selection."""

    Internal = 0x00
    All = 0x01
    External = 0x02
    Occupancy = 0x03


class ControlAlgorithm(t.enum8):
    """Control algorithm for temperature regulation."""

    TPI_UFH = 0x00
    TPI_RAD = 0x01
    TPI_ELE = 0x02
    HIS_02 = 0x03
    HIS_04 = 0x04
    HIS_06 = 0x05
    HIS_08 = 0x06
    HIS_10 = 0x07
    HIS_20 = 0x08
    HIS_30 = 0x09
    HIS_40 = 0x0A


class RelayMode(t.enum8):
    """Relay output mode."""

    NO = 0x00
    NC = 0x01
    OFF = 0x02


class ComfortWarmFloor(t.enum8):
    """Comfort warm floor setting - automatic floor warming interval."""

    OFF = 0x00
    Level1 = 0x01
    Level2 = 0x02
    Level3 = 0x03
    Level4 = 0x04
    Level5 = 0x05


class TempResolution(t.enum8):
    """Temperature display resolution."""

    OneDegree = 0x00
    FiveDegree = 0x01


class SensorError(t.enum8):
    """Sensor error status."""

    Normal = 0x00
    E1 = 0x01
    E2 = 0x02


class EngoThermostat(Thermostat):
    """Tuya local thermostat cluster for ENGO devices."""

    _CONSTANT_ATTRIBUTES = {
        Thermostat.AttributeDefs.ctrl_sequence_of_oper.id: Thermostat.ControlSequenceOfOperation.Heating_Only
    }

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Init an EngoThermostat cluster."""
        super().__init__(*args, **kwargs)
        self.add_unsupported_attribute(
            Thermostat.AttributeDefs.setpoint_change_source.id
        )
        self.add_unsupported_attribute(
            Thermostat.AttributeDefs.setpoint_change_source_timestamp.id
        )
        self.add_unsupported_attribute(Thermostat.AttributeDefs.pi_heating_demand.id)
        self.add_unsupported_attribute(
            Thermostat.AttributeDefs.local_temperature_calibration.id
        )


class EngoThermostatMCUCluster(TuyaMCUCluster):
    """Tuya Manufacturer Cluster with time sync for ENGO thermostats."""

    class ServerCommandDefs(TuyaMCUCluster.ServerCommandDefs):
        """Server command definitions."""

        set_time = foundation.ZCLCommandDef(
            id=TUYA_SET_TIME,
            schema={"time": TuyaTimePayload},
            is_manufacturer_specific=False,
        )


# ENGO EONE-230B/W Thermostat
(
    TuyaQuirkBuilder("_TZE200_awnadkan", "TS0601")
    # === CORE THERMOSTAT FUNCTIONALITY ===
    # DP 1: ON/OFF state
    .tuya_dp(
        dp_id=1,
        ep_attribute=EngoThermostat.ep_attribute,
        attribute_name=EngoThermostat.AttributeDefs.system_mode.name,
        converter=lambda x: Thermostat.SystemMode.Off
        if not x
        else Thermostat.SystemMode.Heat,
        dp_converter=lambda x: x != Thermostat.SystemMode.Off,
    )
    # DP 2: System mode - heating or cooling
    .tuya_enum(
        dp_id=2,
        attribute_name="system_mode_select",
        enum_class=SystemMode,
        translation_key="system_mode",
        fallback_name="System mode",
    )
    # DP 3: Running state - is heating/cooling currently active
    .tuya_dp(
        dp_id=3,
        ep_attribute=EngoThermostat.ep_attribute,
        attribute_name=EngoThermostat.AttributeDefs.running_state.name,
        converter=lambda x: Thermostat.RunningState.Heat_State_On
        if x in (0x01, 0x03)
        else Thermostat.RunningState.Idle,
    )
    # DP 16: Heating/cooling setpoint (device sends decidegrees)
    .tuya_dp(
        dp_id=16,
        ep_attribute=EngoThermostat.ep_attribute,
        attribute_name=EngoThermostat.AttributeDefs.occupied_heating_setpoint.name,
        converter=lambda x: x * 10,
        dp_converter=lambda x: x // 10,
    )
    # DP 19: Maximum temperature limit
    .tuya_dp(
        dp_id=19,
        ep_attribute=EngoThermostat.ep_attribute,
        attribute_name=EngoThermostat.AttributeDefs.max_heat_setpoint_limit.name,
        converter=lambda x: x * 10,
        dp_converter=lambda x: x // 10,
    )
    # DP 24: Current local temperature
    .tuya_dp(
        dp_id=24,
        ep_attribute=EngoThermostat.ep_attribute,
        attribute_name=EngoThermostat.AttributeDefs.local_temperature.name,
        converter=lambda x: x * 10,
    )
    # DP 26: Minimum temperature limit
    .tuya_dp(
        dp_id=26,
        ep_attribute=EngoThermostat.ep_attribute,
        attribute_name=EngoThermostat.AttributeDefs.min_heat_setpoint_limit.name,
        converter=lambda x: x * 10,
        dp_converter=lambda x: x // 10,
    )
    # DP 27: Local temperature calibration offset
    .tuya_number(
        dp_id=27,
        attribute_name="local_temperature_calibration",
        type=t.int16s,
        unit=UnitOfTemperature.CELSIUS,
        min_value=-3.5,
        max_value=3.5,
        step=0.5,
        multiplier=0.1,
        translation_key="local_temperature_calibration",
        fallback_name="Temperature calibration",
    )
    .adds(EngoThermostat)
    # === PRESET / MODE SETTINGS ===
    # DP 58: Operating preset mode
    .tuya_enum(
        dp_id=58,
        attribute_name="preset_mode",
        enum_class=PresetMode,
        translation_key="preset",
        fallback_name="Preset",
    )
    # === SENSORS ===
    # DP 34: Humidity sensor
    .tuya_sensor(
        dp_id=34,
        attribute_name="humidity",
        type=t.int16s,
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
        unit=PERCENTAGE,
        fallback_name="Humidity",
    )
    # DP 116: Floor temperature sensor (returns 32766 when disconnected)
    .tuya_sensor(
        dp_id=116,
        attribute_name="floor_temperature",
        type=t.int16s,
        converter=lambda x: x / 10.0 if x < 32760 else None,
        state_class=SensorStateClass.MEASUREMENT,
        unit=UnitOfTemperature.CELSIUS,
        translation_key="floor_temperature",
        fallback_name="Floor temperature",
    )
    # DP 120: Sensor error status
    .tuya_enum(
        dp_id=120,
        attribute_name="sensor_error",
        enum_class=SensorError,
        translation_key="sensor_error",
        fallback_name="Sensor error",
        entity_type=EntityType.DIAGNOSTIC,
    )
    # === HOLIDAY MODE SETTINGS ===
    # DP 32: Holiday mode temperature setpoint
    .tuya_number(
        dp_id=32,
        attribute_name="holiday_temperature",
        type=t.uint16_t,
        unit=UnitOfTemperature.CELSIUS,
        min_value=5,
        max_value=45,
        step=0.5,
        multiplier=0.1,
        translation_key="holiday_temperature",
        fallback_name="Holiday temperature",
    )
    # DP 33: Holiday mode duration in days
    .tuya_number(
        dp_id=33,
        attribute_name="holiday_days",
        type=t.uint16_t,
        min_value=1,
        max_value=30,
        step=1,
        translation_key="holiday_days",
        fallback_name="Holiday days",
    )
    # === FROST PROTECTION ===
    # DP 106: Frost protection temperature setpoint
    .tuya_number(
        dp_id=106,
        attribute_name="frost_protection_temperature",
        type=t.uint16_t,
        unit=UnitOfTemperature.CELSIUS,
        min_value=5,
        max_value=17,
        step=0.5,
        multiplier=0.1,
        translation_key="frost_protection_temperature",
        fallback_name="Frost protection temperature",
    )
    # === DEVICE CONTROLS ===
    # DP 40: Child lock - prevents physical button presses
    .tuya_switch(
        dp_id=40,
        attribute_name="child_lock",
        translation_key="child_lock",
        fallback_name="Child lock",
    )
    # DP 44: Backlight brightness (0-100%)
    .tuya_number(
        dp_id=44,
        attribute_name="backlight_brightness",
        type=t.uint16_t,
        unit=PERCENTAGE,
        min_value=0,
        max_value=100,
        step=10,
        translation_key="backlight",
        fallback_name="Backlight brightness",
    )
    # === ADVANCED SETTINGS ===
    # DP 43: Temperature sensor selection
    .tuya_enum(
        dp_id=43,
        attribute_name="sensor_select",
        enum_class=SensorSelect,
        translation_key="sensor_select",
        fallback_name="Sensor selection",
    )
    # DP 101: Control algorithm
    .tuya_enum(
        dp_id=101,
        attribute_name="control_algorithm",
        enum_class=ControlAlgorithm,
        translation_key="control_algorithm",
        fallback_name="Control algorithm",
    )
    # DP 107: Valve protection - prevents valve blockage during inactivity
    .tuya_switch(
        dp_id=107,
        attribute_name="valve_protection",
        translation_key="valve_protection",
        fallback_name="Valve protection",
    )
    # DP 108: Relay output mode
    .tuya_enum(
        dp_id=108,
        attribute_name="relay_mode",
        enum_class=RelayMode,
        translation_key="relay_mode",
        fallback_name="Relay mode",
    )
    # DP 117: Temperature display resolution
    .tuya_enum(
        dp_id=117,
        attribute_name="temperature_resolution",
        enum_class=TempResolution,
        translation_key="temperature_resolution",
        fallback_name="Temperature resolution",
    )
    # DP 118: Comfort warm floor - periodic floor warming
    .tuya_enum(
        dp_id=118,
        attribute_name="comfort_warm_floor",
        enum_class=ComfortWarmFloor,
        translation_key="comfort_warm_floor",
        fallback_name="Comfort warm floor",
    )
    # === WEEKLY SCHEDULE (DPs 109-115) ===
    # Format: "HH:MM/TEMP HH:MM/TEMP ..." (Z2M compatible)
    # Example: "06:00/21.0 08:00/18.0 12:00/20.0 14:00/18.0 18:00/21.0 22:00/18.0"
    # DP 109: Monday schedule
    .tuya_dp(
        dp_id=109,
        ep_attribute=EngoThermostatMCUCluster.ep_attribute,
        attribute_name="schedule_monday",
        converter=parse_schedule,
        dp_converter=lambda x: format_schedule(x, 1),
    )
    # DP 110: Tuesday schedule
    .tuya_dp(
        dp_id=110,
        ep_attribute=EngoThermostatMCUCluster.ep_attribute,
        attribute_name="schedule_tuesday",
        converter=parse_schedule,
        dp_converter=lambda x: format_schedule(x, 2),
    )
    # DP 111: Wednesday schedule
    .tuya_dp(
        dp_id=111,
        ep_attribute=EngoThermostatMCUCluster.ep_attribute,
        attribute_name="schedule_wednesday",
        converter=parse_schedule,
        dp_converter=lambda x: format_schedule(x, 3),
    )
    # DP 112: Thursday schedule
    .tuya_dp(
        dp_id=112,
        ep_attribute=EngoThermostatMCUCluster.ep_attribute,
        attribute_name="schedule_thursday",
        converter=parse_schedule,
        dp_converter=lambda x: format_schedule(x, 4),
    )
    # DP 113: Friday schedule
    .tuya_dp(
        dp_id=113,
        ep_attribute=EngoThermostatMCUCluster.ep_attribute,
        attribute_name="schedule_friday",
        converter=parse_schedule,
        dp_converter=lambda x: format_schedule(x, 5),
    )
    # DP 114: Saturday schedule
    .tuya_dp(
        dp_id=114,
        ep_attribute=EngoThermostatMCUCluster.ep_attribute,
        attribute_name="schedule_saturday",
        converter=parse_schedule,
        dp_converter=lambda x: format_schedule(x, 6),
    )
    # DP 115: Sunday schedule
    .tuya_dp(
        dp_id=115,
        ep_attribute=EngoThermostatMCUCluster.ep_attribute,
        attribute_name="schedule_sunday",
        converter=parse_schedule,
        dp_converter=lambda x: format_schedule(x, 7),
    )
    .skip_configuration()
    .add_to_registry(replacement_cluster=EngoThermostatMCUCluster)
)
