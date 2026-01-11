""" Thermostat v9bw from Tuya TS0601/_TZE204_wc2w9t1s """

from zigpy.quirks.v2.homeassistant import EntityPlatform, EntityType, UnitOfTemperature
import zigpy.types as t
from zigpy.zcl.clusters.hvac import RunningState, Thermostat

from zhaquirks.tuya.builder import TuyaQuirkBuilder
from zhaquirks.tuya.tuya_trv import TuyaThermostatV2


class PresetMode(t.enum8):
    """Preset mode enum."""
    Auto = 0x00
    Manual = 0x01
    Eco = 0x02


def _deci_c_to_zigbee_0_01(v: int) -> int:
    return int(v) * 10


def _zigbee_0_01_to_deci_c(v: int) -> int:
    return int(v) // 10


def _is_open(v) -> bool:
    return v in (1, True, "open", "OPEN")


def _schedule_raw_to_str(v) -> str:
    """Convert schedule to raw hex string."""
    if v is None:
        return ""
    if isinstance(v, (bytes, bytearray)):
        return v.hex()
    return str(v)


(
    TuyaQuirkBuilder("_TZE204_wc2w9t1s", "TS0601")
    # DP 1: heat/off
    .tuya_dp(
        dp_id=1,
        ep_attribute=TuyaThermostatV2.ep_attribute,
        attribute_name=TuyaThermostatV2.AttributeDefs.system_mode.name,
        converter=lambda v: Thermostat.SystemMode.Heat
        if bool(v)
        else Thermostat.SystemMode.Off,
        dp_converter=lambda v: True if v == Thermostat.SystemMode.Heat else False,
    )
    # DP 2: preset enum
    .tuya_enum(
        dp_id=2,
        attribute_name="preset",
        enum_class=PresetMode,
        entity_platform=EntityPlatform.SELECT,
        entity_type=EntityType.CONFIG,
        translation_key="preset",
        fallback_name="Preset",
    )
    # DP 10: frost switch
    .tuya_switch(
        dp_id=10,
        attribute_name="frost",
        entity_type=EntityType.CONFIG,
        translation_key="frost",
        fallback_name="Frost protection",
    )
    # DP 16: setpoint 0.1°C -> 0.01°C
    .tuya_dp(
        dp_id=16,
        ep_attribute=TuyaThermostatV2.ep_attribute,
        attribute_name=TuyaThermostatV2.AttributeDefs.occupied_heating_setpoint.name,
        converter=_deci_c_to_zigbee_0_01,
        dp_converter=_zigbee_0_01_to_deci_c,
    )
    # DP 18/19: min/max limits (°C 0.1)
    .tuya_number(
        dp_id=18,
        attribute_name="min_temperature_limit",
        type=t.int16s,
        multiplier=0.1,
        min_value=5,
        max_value=30,
        step=0.5,
        unit=UnitOfTemperature.CELSIUS,
        entity_type=EntityType.CONFIG,
        translation_key="min_temperature_limit",
        fallback_name="Min temperature limit",
    )
    .tuya_number(
        dp_id=19,
        attribute_name="max_temperature_limit",
        type=t.int16s,
        multiplier=0.1,
        min_value=15,
        max_value=60,
        step=0.5,
        unit=UnitOfTemperature.CELSIUS,
        entity_type=EntityType.CONFIG,
        translation_key="max_temperature_limit",
        fallback_name="Max temperature limit",
    )
    # DP 24: local temp 0.1°C -> 0.01°C
    .tuya_dp(
        dp_id=24,
        ep_attribute=TuyaThermostatV2.ep_attribute,
        attribute_name=TuyaThermostatV2.AttributeDefs.local_temperature.name,
        converter=_deci_c_to_zigbee_0_01,
    )
    # DP 36: running_state heat/idle
    .tuya_dp(
        dp_id=36,
        ep_attribute=TuyaThermostatV2.ep_attribute,
        attribute_name=TuyaThermostatV2.AttributeDefs.running_state.name,
        converter=lambda v: RunningState.Heat_State_On
        if _is_open(v)
        else RunningState.Idle,
    )
    # DP 40: child lock
    .tuya_switch(
        dp_id=40,
        attribute_name="child_lock",
        entity_type=EntityType.CONFIG,
        translation_key="child_lock",
        fallback_name="Child lock",
    )
    # DP 107: battery
    .tuya_battery(dp_id=107)
    # DP 109: calibration 0.1°C -> 0.01°C
    .tuya_dp(
        dp_id=109,
        ep_attribute=TuyaThermostatV2.ep_attribute,
        attribute_name="local_temperature_calibration",
        converter=_deci_c_to_zigbee_0_01,
        dp_converter=_zigbee_0_01_to_deci_c,
    )
    # DP 112/116: deadzone + eco temp
    .tuya_number(
        dp_id=112,
        attribute_name="deadzone_temperature",
        type=t.int16s,
        multiplier=0.1,
        min_value=0,
        max_value=0.5,
        step=0.1,
        unit=UnitOfTemperature.CELSIUS,
        entity_type=EntityType.CONFIG,
        translation_key="deadzone_temperature",
        fallback_name="Deadzone",
    )
    .tuya_number(
        dp_id=116,
        attribute_name="eco_temperature",
        type=t.int16s,
        multiplier=0.1,
        unit=UnitOfTemperature.CELSIUS,
        entity_type=EntityType.CONFIG,
        translation_key="eco_temperature",
        fallback_name="Eco temperature",
    )
    # DP 65-71: schedules (raw hex)
    .tuya_sensor(
        dp_id=65,
        attribute_name="schedule_monday",
        type=t.LVBytes,
        converter=_schedule_raw_to_str,
        entity_type=EntityType.DIAGNOSTIC,
        translation_key="schedule_monday",
        fallback_name="Schedule Monday",
    )
    .tuya_sensor(
        dp_id=66,
        attribute_name="schedule_tuesday",
        type=t.LVBytes,
        converter=_schedule_raw_to_str,
        entity_type=EntityType.DIAGNOSTIC,
        translation_key="schedule_tuesday",
        fallback_name="Schedule Tuesday",
    )
    .tuya_sensor(
        dp_id=67,
        attribute_name="schedule_wednesday",
        type=t.LVBytes,
        converter=_schedule_raw_to_str,
        entity_type=EntityType.DIAGNOSTIC,
        translation_key="schedule_wednesday",
        fallback_name="Schedule Wednesday",
    )
    .tuya_sensor(
        dp_id=68,
        attribute_name="schedule_thursday",
        type=t.LVBytes,
        converter=_schedule_raw_to_str,
        entity_type=EntityType.DIAGNOSTIC,
        translation_key="schedule_thursday",
        fallback_name="Schedule Thursday",
    )
    .tuya_sensor(
        dp_id=69,
        attribute_name="schedule_friday",
        type=t.LVBytes,
        converter=_schedule_raw_to_str,
        entity_type=EntityType.DIAGNOSTIC,
        translation_key="schedule_friday",
        fallback_name="Schedule Friday",
    )
    .tuya_sensor(
        dp_id=70,
        attribute_name="schedule_saturday",
        type=t.LVBytes,
        converter=_schedule_raw_to_str,
        entity_type=EntityType.DIAGNOSTIC,
        translation_key="schedule_saturday",
        fallback_name="Schedule Saturday",
    )
    .tuya_sensor(
        dp_id=71,
        attribute_name="schedule_sunday",
        type=t.LVBytes,
        converter=_schedule_raw_to_str,
        entity_type=EntityType.DIAGNOSTIC,
        translation_key="schedule_sunday",
        fallback_name="Schedule Sunday",
    )
    .adds(TuyaThermostatV2)
    .skip_configuration()
    .add_to_registry()
)
