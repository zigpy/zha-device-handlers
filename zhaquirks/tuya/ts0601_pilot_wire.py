"""Tuya TS0601 pilot wire (fil pilote) heating controller.

Powernity / Xanlite PO-BOCO-ELEC: a Zigbee box that drives French electric
radiators through the "fil pilote" wire. The fil pilote standard defines up to
6 heating modes sent to the radiator using AC phase modulation.

Data points, cross-checked with the zigbee-herdsman-converters PO-BOCO-ELEC
definition and on a real _TZE204_3q3maeoo device:
  DP   2 - Operating mode (Auto / Manual / Holiday)
  DP   8 - Relative humidity in %
  DP  11 - Energy consumed in kWh (estimated from the power rating)
  DP  16 - Local temperature in 0.1 °C
  DP  39 - Child lock
  DP 101 - Local temperature calibration in 0.1 °C
  DP 108 - Boost heating
  DP 123 - Boost time remaining in s (900 to 0)
  DP 126 - Pilot wire mode applied in Auto
  DP 127 - Pilot wire mode applied in Manual
  DP 136 - Frost protection
  DP 138 - Open window detection
  DP 139 - Pilot wire mode while a window is open
  DP 140 - Open window mode duration in min
  DP 141 - Reset energy consumption
  DP 142 - Heater power rating in W
  DP 144 - Number of modes supported by the heater (4 or 6)

Not exposed: DP 46 (temperature unit), DP 143 (holiday start/stop) and the
weekly schedule data points.
"""

import zigpy.types as t

from zhaquirks.builder import (
    EntityType,
    SensorDeviceClass,
    SensorStateClass,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfTemperature,
    UnitOfTime,
)
from zhaquirks.tuya import TUYA_CLUSTER_ID
from zhaquirks.tuya.builder import TuyaQuirkBuilder


class OperatingMode(t.enum8):
    """Operating mode."""

    Auto = 0x00
    Manual = 0x01
    Holiday = 0x02


class PilotWireMode(t.enum8):
    """Fil pilote heating mode."""

    Comfort = 0x00
    ComfortMinus1 = 0x01
    ComfortMinus2 = 0x02
    Eco = 0x03
    AntiFrost = 0x04
    Off = 0x05


class ModeSwitching(t.enum8):
    """Number of fil pilote modes supported by the heater."""

    FourModes = 0x00
    SixModes = 0x01


(
    TuyaQuirkBuilder("_TZE204_3q3maeoo", "TS0601")
    .tuya_enum(
        dp_id=2,
        attribute_name="operating_mode",
        enum_class=OperatingMode,
        entity_type=EntityType.STANDARD,
        translation_key="operating_mode",
        fallback_name="Operating mode",
    )
    .tuya_enum(
        dp_id=127,
        attribute_name="pilot_wire_mode",
        enum_class=PilotWireMode,
        entity_type=EntityType.STANDARD,
        translation_key="pilot_wire_mode",
        fallback_name="Pilot wire mode",
    )
    .tuya_enum(
        dp_id=126,
        attribute_name="auto_pilot_wire_mode",
        enum_class=PilotWireMode,
        translation_key="auto_pilot_wire_mode",
        fallback_name="Auto mode pilot wire mode",
    )
    .tuya_switch(
        dp_id=108,
        attribute_name="boost_heating",
        entity_type=EntityType.STANDARD,
        translation_key="boost_heating",
        fallback_name="Boost heating",
    )
    .tuya_sensor(
        dp_id=123,
        attribute_name="boost_time_remaining",
        type=t.uint32_t,
        device_class=SensorDeviceClass.DURATION,
        unit=UnitOfTime.SECONDS,
        translation_key="boost_time_remaining",
        fallback_name="Boost time remaining",
    )
    .tuya_temperature(dp_id=16, scale=10)
    .tuya_humidity(dp_id=8)
    .tuya_sensor(
        dp_id=11,
        attribute_name="energy_consumed",
        type=t.uint32_t,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        unit=UnitOfEnergy.KILO_WATT_HOUR,
        translation_key="energy_consumed",
        fallback_name="Energy consumed",
    )
    .tuya_number(
        dp_id=101,
        type=t.int32s,
        attribute_name="local_temperature_calibration",
        min_value=-5.5,
        max_value=5.5,
        step=0.5,
        multiplier=0.1,
        unit=UnitOfTemperature.CELSIUS,
        translation_key="local_temperature_calibration",
        fallback_name="Local temperature calibration",
    )
    .tuya_switch(
        dp_id=39,
        attribute_name="child_lock",
        translation_key="child_lock",
        fallback_name="Child lock",
    )
    .tuya_switch(
        dp_id=136,
        attribute_name="frost_protection",
        translation_key="frost_protection",
        fallback_name="Frost protection",
    )
    .tuya_switch(
        dp_id=138,
        attribute_name="window_detection",
        translation_key="window_detection",
        fallback_name="Open window detection",
    )
    .tuya_enum(
        dp_id=139,
        attribute_name="window_opening_mode",
        enum_class=PilotWireMode,
        translation_key="window_opening_mode",
        fallback_name="Open window mode",
    )
    .tuya_number(
        dp_id=140,
        type=t.uint32_t,
        attribute_name="window_opening_mode_duration",
        min_value=1,
        max_value=90,
        step=1,
        unit=UnitOfTime.MINUTES,
        translation_key="window_opening_mode_duration",
        fallback_name="Open window mode duration",
    )
    .tuya_number(
        dp_id=142,
        type=t.uint32_t,
        attribute_name="power_rating",
        min_value=10,
        max_value=10000,
        step=10,
        unit=UnitOfPower.WATT,
        translation_key="power_rating",
        fallback_name="Heater power rating",
    )
    .tuya_enum(
        dp_id=144,
        attribute_name="mode_switching",
        enum_class=ModeSwitching,
        translation_key="mode_switching",
        fallback_name="Supported modes",
    )
    .tuya_dp_attribute(
        dp_id=141,
        attribute_name="reset_energy_consumption",
        type=t.Bool,
    )
    .write_attr_button(
        attribute_name="reset_energy_consumption",
        cluster_id=TUYA_CLUSTER_ID,
        attribute_value=0x01,
        translation_key="reset_energy_consumption",
        fallback_name="Reset energy consumption",
    )
    .skip_configuration()
    .add_to_registry()
)
