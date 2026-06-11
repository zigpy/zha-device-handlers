"""Tuya Power Meter."""

import zigpy.types as t
from zigpy.zcl.clusters.general import LevelControl, OnOff
from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement

from zhaquirks.builder import (
    PERCENTAGE,
    EntityType,
    SensorDeviceClass,
    SensorStateClass,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfFrequency,
    UnitOfPower,
    UnitOfTemperature,
    UnitOfTime,
)
from zhaquirks.tuya import TuyaLocalCluster
from zhaquirks.tuya.builder import TuyaQuirkBuilder
from zhaquirks.tuya.mcu import DPToAttributeMapping

# Enum used by 1-phase Tongou TO-Q-SA1 Power Meter: TOSA1-01WXJAT1A, _TZE284_pglpvdar, TS0601
class OnlineState(t.enum8):
    Online = 0
    Offline = 1

# Enum used by 1-phase Tongou TO-Q-SA1 Power Meter: TOSA1-01WXJAT1A, _TZE284_pglpvdar, TS0601
class AlertEvent(t.enum8):
    Normal = 0

    Over_Current_Trip = 1
    Over_Power_Trip = 2
    High_Temp_Trip = 3
    Over_Voltage_Trip = 4
    Under_Voltage_Trip = 5

    Over_Current_Alarm = 6
    Over_Power_Alarm = 7
    High_Temp_Alarm = 8
    Over_Voltage_Alarm = 9
    Under_Voltage_Alarm = 10

    Remote_ON = 11
    Remote_OFF = 12

    Manual_ON = 13
    Manual_OFF = 14

    Leakage_Trip = 15
    Leakage_Alarm = 16

    Restore_Default = 17
    Automatic_Closing = 18

    Electricity_Shortage = 19
    Electricity_Shortage_Alarm = 20

    Timing_Switch_ON = 21
    Timing_Switch_OFF = 22

    Electricity_Reset = 23


def dp_to_power(data: bytes) -> int:
    """Convert DP data to power value."""
    # From https://github.com/Koenkk/zigbee2mqtt/issues/18603#issuecomment-2277697295
    power = int(data)
    if power > 0x0FFFFFFF:
        power = (0x1999999C - power) * -1
    return power


def multi_dp_to_power(data: bytes) -> int:
    """Convert DP data to power value."""
    # Support negative power readings
    # From https://github.com/Koenkk/zigbee2mqtt/issues/18603#issuecomment-2277697295
    power = data[7] | (data[6] << 8)
    if power > 0x7FFF:
        power = (0x999A - power) * -1
    return power


def multi_dp_to_current(data: bytes) -> int:
    """Convert DP data to current value."""
    return data[4] | (data[3] << 8)


def multi_dp_to_voltage(data: bytes) -> int:
    """Convert DP data to voltage value."""
    return data[1] | (data[0] << 8)


class TuyaElectricalMeasurement(ElectricalMeasurement, TuyaLocalCluster):
    """Tuya Electrical Measurement cluster."""

    _CONSTANT_ATTRIBUTES = {
        ElectricalMeasurement.AttributeDefs.ac_current_multiplier.id: 1,
        ElectricalMeasurement.AttributeDefs.ac_current_divisor.id: 1000,
        ElectricalMeasurement.AttributeDefs.ac_voltage_multiplier.id: 1,
        ElectricalMeasurement.AttributeDefs.ac_voltage_divisor.id: 10,
    }


(
    TuyaQuirkBuilder("_TZE200_nslr42tt", "TS0601")
    .tuya_temperature(dp_id=133, scale=10)
    .tuya_sensor(
        dp_id=134,
        attribute_name="device_status",
        type=t.int32s,
        fallback_name="Device status",
        translation_key="device_status",
    )
    .tuya_dp(
        dp_id=132,
        ep_attribute=TuyaElectricalMeasurement.ep_attribute,
        attribute_name="ac_frequency",
    )
    # Energy
    .tuya_sensor(
        dp_id=1,
        attribute_name="energy",
        type=t.int32s,
        divisor=100,
        state_class=SensorStateClass.TOTAL,
        device_class=SensorDeviceClass.ENERGY,
        unit=UnitOfEnergy.KILO_WATT_HOUR,
        fallback_name="Total energy",
    )
    .tuya_sensor(
        dp_id=101,
        attribute_name="energy_ph_a",
        type=t.int32s,
        divisor=1000,
        state_class=SensorStateClass.TOTAL,
        device_class=SensorDeviceClass.ENERGY,
        unit=UnitOfEnergy.KILO_WATT_HOUR,
        translation_key="energy_ph_a",
        fallback_name="Energy phase A",
    )
    .tuya_sensor(
        dp_id=111,
        attribute_name="energy_ph_b",
        type=t.int32s,
        divisor=1000,
        state_class=SensorStateClass.TOTAL,
        device_class=SensorDeviceClass.ENERGY,
        unit=UnitOfEnergy.KILO_WATT_HOUR,
        translation_key="energy_ph_b",
        fallback_name="Energy phase B",
    )
    .tuya_sensor(
        dp_id=121,
        attribute_name="energy_ph_c",
        type=t.int32s,
        divisor=1000,
        state_class=SensorStateClass.TOTAL,
        device_class=SensorDeviceClass.ENERGY,
        unit=UnitOfEnergy.KILO_WATT_HOUR,
        translation_key="energy_ph_c",
        fallback_name="Energy phase C",
    )
    .tuya_sensor(
        dp_id=9,
        attribute_name="power",
        type=t.int32s,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.POWER,
        unit=UnitOfPower.WATT,
        fallback_name="Total power",
        converter=dp_to_power,
    )
    .tuya_sensor(
        dp_id=131,
        attribute_name="current",
        type=t.int32s,
        divisor=1000,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.CURRENT,
        unit=UnitOfElectricCurrent.AMPERE,
        fallback_name="Total current",
    )
    .tuya_dp_multi(
        dp_id=6,
        attribute_mapping=[
            DPToAttributeMapping(
                ep_attribute=TuyaElectricalMeasurement.ep_attribute,
                attribute_name="active_power",
                converter=multi_dp_to_power,
            ),
            DPToAttributeMapping(
                ep_attribute=TuyaElectricalMeasurement.ep_attribute,
                attribute_name="rms_voltage",
                converter=multi_dp_to_voltage,
            ),
            DPToAttributeMapping(
                ep_attribute=TuyaElectricalMeasurement.ep_attribute,
                attribute_name="rms_current",
                converter=multi_dp_to_current,
            ),
        ],
    )
    .tuya_dp_multi(
        dp_id=7,
        attribute_mapping=[
            DPToAttributeMapping(
                ep_attribute=TuyaElectricalMeasurement.ep_attribute,
                attribute_name="active_power_ph_b",
                converter=multi_dp_to_power,
            ),
            DPToAttributeMapping(
                ep_attribute=TuyaElectricalMeasurement.ep_attribute,
                attribute_name="rms_voltage_ph_b",
                converter=multi_dp_to_voltage,
            ),
            DPToAttributeMapping(
                ep_attribute=TuyaElectricalMeasurement.ep_attribute,
                attribute_name="rms_current_ph_b",
                converter=multi_dp_to_current,
            ),
        ],
    )
    .tuya_dp_multi(
        dp_id=8,
        attribute_mapping=[
            DPToAttributeMapping(
                ep_attribute=TuyaElectricalMeasurement.ep_attribute,
                attribute_name="active_power_ph_c",
                converter=multi_dp_to_power,
            ),
            DPToAttributeMapping(
                ep_attribute=TuyaElectricalMeasurement.ep_attribute,
                attribute_name="rms_voltage_ph_c",
                converter=multi_dp_to_voltage,
            ),
            DPToAttributeMapping(
                ep_attribute=TuyaElectricalMeasurement.ep_attribute,
                attribute_name="rms_current_ph_c",
                converter=multi_dp_to_current,
            ),
        ],
    )
    .tuya_dp(
        dp_id=102,
        ep_attribute=TuyaElectricalMeasurement.ep_attribute,
        attribute_name="power_factor",
    )
    .tuya_dp(
        dp_id=112,
        ep_attribute=TuyaElectricalMeasurement.ep_attribute,
        attribute_name="power_factor_ph_b",
    )
    .tuya_dp(
        dp_id=122,
        ep_attribute=TuyaElectricalMeasurement.ep_attribute,
        attribute_name="power_factor_ph_c",
    )
    .adds(TuyaElectricalMeasurement)
    .removes(LevelControl.cluster_id)
    .removes(OnOff.cluster_id)
    .skip_configuration()
    .add_to_registry()
)

(
    TuyaQuirkBuilder("_TZE200_dikb3dp6", "TS0601")
    .applies_to("_TZE204_dikb3dp6", "TS0601")
    .applies_to("_TZE284_dikb3dp6", "TS0601")
    .applies_to("_TZE284_wbhaespm", "TS0601")  # reported in #4277
    .tuya_sensor(
        dp_id=1,
        attribute_name="energy",
        type=t.int32s,
        divisor=100,
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.ENERGY,
        unit=UnitOfEnergy.KILO_WATT_HOUR,
        fallback_name="Total energy",
    )
    .tuya_sensor(
        dp_id=23,
        attribute_name="energy_produced",
        type=t.uint32_t,
        divisor=100,
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.ENERGY,
        unit=UnitOfEnergy.KILO_WATT_HOUR,
        translation_key="energy_produced",
        fallback_name="Energy produced",
    )
    .tuya_dp(
        dp_id=29,
        ep_attribute=TuyaElectricalMeasurement.ep_attribute,
        attribute_name="total_active_power",
    )
    .tuya_dp(
        dp_id=32,
        ep_attribute=TuyaElectricalMeasurement.ep_attribute,
        attribute_name="ac_frequency",
        converter=lambda x: x / 100,
    )
    .tuya_sensor(
        dp_id=50,
        attribute_name="power_factor",
        type=t.uint8_t,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.POWER_FACTOR,
        unit=PERCENTAGE,
        translation_key="total_power_factor",
        fallback_name="Total power factor",
    )
    .tuya_number(
        dp_id=102,
        attribute_name="update_frequency",
        type=t.uint16_t,
        device_class=SensorDeviceClass.DURATION,
        unit=UnitOfTime.SECONDS,
        min_value=5,
        max_value=3600,
        step=1,
        entity_type=EntityType.CONFIG,
        translation_key="update_frequency",
        fallback_name="Update frequency",
    )
    # Phase A
    .tuya_dp(
        dp_id=103,
        ep_attribute=TuyaElectricalMeasurement.ep_attribute,
        attribute_name="rms_voltage",
    )
    .tuya_dp(
        dp_id=104,
        ep_attribute=TuyaElectricalMeasurement.ep_attribute,
        attribute_name="rms_current",
    )
    .tuya_dp(
        dp_id=105,
        ep_attribute=TuyaElectricalMeasurement.ep_attribute,
        attribute_name="active_power",
    )
    .tuya_dp(
        dp_id=108,
        ep_attribute=TuyaElectricalMeasurement.ep_attribute,
        attribute_name="power_factor",
    )
    .tuya_sensor(
        dp_id=109,
        attribute_name="energy_consumed_ph_a",
        type=t.uint32_t,
        divisor=100,
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.ENERGY,
        unit=UnitOfEnergy.KILO_WATT_HOUR,
        translation_key="energy_ph_a",
        fallback_name="Energy phase A",
    )
    .tuya_sensor(
        dp_id=110,
        attribute_name="energy_produced_ph_a",
        type=t.uint32_t,
        divisor=100,
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.ENERGY,
        unit=UnitOfEnergy.KILO_WATT_HOUR,
        translation_key="energy_produced_ph_a",
        fallback_name="Energy produced phase A",
    )
    # Phase B
    .tuya_dp(
        dp_id=112,
        ep_attribute=TuyaElectricalMeasurement.ep_attribute,
        attribute_name="rms_voltage_ph_b",
    )
    .tuya_dp(
        dp_id=113,
        ep_attribute=TuyaElectricalMeasurement.ep_attribute,
        attribute_name="rms_current_ph_b",
    )
    .tuya_dp(
        dp_id=114,
        ep_attribute=TuyaElectricalMeasurement.ep_attribute,
        attribute_name="active_power_ph_b",
    )
    .tuya_dp(
        dp_id=117,
        ep_attribute=TuyaElectricalMeasurement.ep_attribute,
        attribute_name="power_factor_ph_b",
    )
    .tuya_sensor(
        dp_id=118,
        attribute_name="energy_consumed_ph_b",
        type=t.uint32_t,
        divisor=100,
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.ENERGY,
        unit=UnitOfEnergy.KILO_WATT_HOUR,
        translation_key="energy_ph_b",
        fallback_name="Energy phase B",
    )
    .tuya_sensor(
        dp_id=119,
        attribute_name="energy_produced_ph_b",
        type=t.uint32_t,
        divisor=100,
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.ENERGY,
        unit=UnitOfEnergy.KILO_WATT_HOUR,
        translation_key="energy_produced_ph_b",
        fallback_name="Energy produced phase B",
    )
    # Phase C
    .tuya_dp(
        dp_id=121,
        ep_attribute=TuyaElectricalMeasurement.ep_attribute,
        attribute_name="rms_voltage_ph_c",
    )
    .tuya_dp(
        dp_id=122,
        ep_attribute=TuyaElectricalMeasurement.ep_attribute,
        attribute_name="rms_current_ph_c",
    )
    .tuya_dp(
        dp_id=123,
        ep_attribute=TuyaElectricalMeasurement.ep_attribute,
        attribute_name="active_power_ph_c",
    )
    .tuya_dp(
        dp_id=126,
        ep_attribute=TuyaElectricalMeasurement.ep_attribute,
        attribute_name="power_factor_ph_c",
    )
    .tuya_sensor(
        dp_id=127,
        attribute_name="energy_consumed_ph_c",
        divisor=100,
        type=t.uint32_t,
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.ENERGY,
        unit=UnitOfEnergy.KILO_WATT_HOUR,
        translation_key="energy_ph_c",
        fallback_name="Energy phase C",
    )
    .tuya_sensor(
        dp_id=128,
        attribute_name="energy_produced_ph_c",
        type=t.uint32_t,
        divisor=100,
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.ENERGY,
        unit=UnitOfEnergy.KILO_WATT_HOUR,
        translation_key="energy_produced_ph_c",
        fallback_name="Energy produced phase C",
    )
    .adds(TuyaElectricalMeasurement)
    .skip_configuration()
    .add_to_registry()
)

(
    TuyaQuirkBuilder("_TZE284_a14rjslz", "TS0601")
    # Metering
    .tuya_sensor(
        dp_id=1,
        attribute_name="energy_consumed",
        type=t.uint32_t,
        divisor=100,
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.ENERGY,
        unit=UnitOfEnergy.KILO_WATT_HOUR,
        fallback_name="Energy",
    )
    .tuya_sensor(
        dp_id=23,
        attribute_name="energy_produced",
        type=t.uint32_t,
        divisor=100,
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.ENERGY,
        unit=UnitOfEnergy.KILO_WATT_HOUR,
        translation_key="energy_produced",
        fallback_name="Energy produced",
    )
    # ElectricalMeasurement
    .tuya_dp(
        dp_id=29,
        ep_attribute=TuyaElectricalMeasurement.ep_attribute,
        attribute_name="total_active_power",
    )
    .tuya_dp(
        dp_id=30,
        ep_attribute=TuyaElectricalMeasurement.ep_attribute,
        attribute_name="total_reactive_power",
    )
    .tuya_dp_multi(
        dp_id=6,
        attribute_mapping=[
            DPToAttributeMapping(
                ep_attribute=TuyaElectricalMeasurement.ep_attribute,
                attribute_name="active_power",
                converter=multi_dp_to_power,
            ),
            DPToAttributeMapping(
                ep_attribute=TuyaElectricalMeasurement.ep_attribute,
                attribute_name="rms_voltage",
                converter=multi_dp_to_voltage,
            ),
            DPToAttributeMapping(
                ep_attribute=TuyaElectricalMeasurement.ep_attribute,
                attribute_name="rms_current",
                converter=multi_dp_to_current,
            ),
        ],
    )
    .tuya_dp_multi(
        dp_id=7,
        attribute_mapping=[
            DPToAttributeMapping(
                ep_attribute=TuyaElectricalMeasurement.ep_attribute,
                attribute_name="active_power_ph_b",
                converter=multi_dp_to_power,
            ),
            DPToAttributeMapping(
                ep_attribute=TuyaElectricalMeasurement.ep_attribute,
                attribute_name="rms_voltage_ph_b",
                converter=multi_dp_to_voltage,
            ),
            DPToAttributeMapping(
                ep_attribute=TuyaElectricalMeasurement.ep_attribute,
                attribute_name="rms_current_ph_b",
                converter=multi_dp_to_current,
            ),
        ],
    )
    .tuya_dp_multi(
        dp_id=8,
        attribute_mapping=[
            DPToAttributeMapping(
                ep_attribute=TuyaElectricalMeasurement.ep_attribute,
                attribute_name="active_power_ph_c",
                converter=multi_dp_to_power,
            ),
            DPToAttributeMapping(
                ep_attribute=TuyaElectricalMeasurement.ep_attribute,
                attribute_name="rms_voltage_ph_c",
                converter=multi_dp_to_voltage,
            ),
            DPToAttributeMapping(
                ep_attribute=TuyaElectricalMeasurement.ep_attribute,
                attribute_name="rms_current_ph_c",
                converter=multi_dp_to_current,
            ),
        ],
    )
    .tuya_dp(
        dp_id=50,
        ep_attribute=TuyaElectricalMeasurement.ep_attribute,
        attribute_name="power_factor",
    )
    .adds(TuyaElectricalMeasurement)
    .skip_configuration()
    .add_to_registry()
)

(
    TuyaQuirkBuilder("_TZE284_pglpvdar", "TS0601")
    # Register DP 6 for the custom cluster to handle
    .tuya_dp_multi(
        dp_id=6,
        attribute_mapping=[
            DPToAttributeMapping(
                ep_attribute=TuyaElectricalMeasurement.ep_attribute,
                attribute_name="rms_voltage",
                converter=multi_dp_to_voltage,
            ),
            DPToAttributeMapping(
                ep_attribute=TuyaElectricalMeasurement.ep_attribute,
                attribute_name="rms_current",
                converter=multi_dp_to_current,
            ),
            DPToAttributeMapping(
                ep_attribute=TuyaElectricalMeasurement.ep_attribute,
                attribute_name="active_power",
                converter=multi_dp_to_power,
            ),
        ],
    )
    
    # Energy
    .tuya_sensor(dp_id=1, attribute_name="energy", translation_key="total_forward_energy",
                 type=t.uint32_t, device_class=SensorDeviceClass.ENERGY,
                 state_class=SensorStateClass.TOTAL_INCREASING,
                 unit=UnitOfEnergy.KILO_WATT_HOUR, divisor=100,
                 fallback_name="Total forward energy")
    .tuya_sensor(dp_id=125, attribute_name="forward_energy", translation_key="forward_energy",
                 type=t.uint32_t, device_class=SensorDeviceClass.ENERGY,
                 state_class=SensorStateClass.TOTAL_INCREASING,
                 unit=UnitOfEnergy.KILO_WATT_HOUR, divisor=100,
                 fallback_name="Forward electricity")
    .tuya_sensor(dp_id=13, attribute_name="remaining_energy", translation_key="remaining_energy",
                 type=t.uint32_t, device_class=SensorDeviceClass.ENERGY_STORAGE,
                 state_class=SensorStateClass.MEASUREMENT,
                 unit=UnitOfEnergy.KILO_WATT_HOUR, divisor=100,
                 fallback_name="Remaining electricity")

    # Advanced measurements
    .tuya_sensor(dp_id=32, attribute_name="ac_frequency", type=t.uint32_t,
                 device_class=SensorDeviceClass.FREQUENCY,
                 state_class=SensorStateClass.MEASUREMENT,
                 unit=UnitOfFrequency.HERTZ, divisor=100,
                 fallback_name="Frequency", translation_key="ac_frequency")
    .tuya_sensor(dp_id=50, attribute_name="power_factor", type=t.uint32_t,
                 device_class=SensorDeviceClass.POWER_FACTOR,
                 state_class=SensorStateClass.MEASUREMENT,
                 divisor=100,
                 fallback_name="Power factor", translation_key="power_factor")
    .tuya_sensor(dp_id=131, attribute_name="temperature", type=t.uint32_t,
                 device_class=SensorDeviceClass.TEMPERATURE,
                 state_class=SensorStateClass.MEASUREMENT,
                 unit=UnitOfTemperature.CELSIUS, divisor=10,
                 fallback_name="CPU temperature")

    # Writable / config DPs
    .tuya_enum(dp_id=109, attribute_name="online_state", translation_key="online_state",
               enum_class=OnlineState, fallback_name="Online state")
    .tuya_enum(dp_id=110, attribute_name="event", translation_key="event",
               enum_class=AlertEvent, fallback_name="Event")

    .tuya_switch(dp_id=11, attribute_name="prepayment_switch", translation_key="prepayment_switch",
                 fallback_name="Prepayment switch")
    .tuya_switch(dp_id=12, attribute_name="clear_remaining_energy", translation_key="clear_remaining_energy",
                 fallback_name="Clear remaining electricity")
    .tuya_switch(dp_id=34, attribute_name="factory_reset", translation_key="factory_reset",
                 fallback_name="Clear forward electricity")
    .tuya_switch(dp_id=113, attribute_name="restore_default", translation_key="restore_default",
                 fallback_name="Restore default alarms/thresholds")

    .tuya_switch(dp_id=101, attribute_name="balance_alarm", translation_key="balance_alarm",
                 fallback_name="Balance alarm")
    .tuya_switch(dp_id=102, attribute_name="overvoltage_alarm", translation_key="overvoltage_alarm",
                 fallback_name="Over-voltage alarm")
    .tuya_switch(dp_id=103, attribute_name="undervoltage_alarm", translation_key="undervoltage_alarm",
                 fallback_name="Under-voltage alarm")
    .tuya_switch(dp_id=104, attribute_name="overcurrent_alarm", translation_key="overcurrent_alarm",
                 fallback_name="Over-current alarm")
    .tuya_switch(dp_id=105, attribute_name="overpower_alarm", translation_key="overpower_alarm",
                 fallback_name="Over-power alarm")
    .tuya_switch(dp_id=107, attribute_name="temperature_alarm", translation_key="temperature_alarm",
                 fallback_name="Temperature alarm")

    # Numeric thresholds
    .tuya_number(dp_id=14, attribute_name="add_electricity_charge", translation_key="add_electricity_charge",
                 type=t.uint32_t, min_value=0, max_value=500, step=1, multiplier=0.01, unit=UnitOfEnergy.KILO_WATT_HOUR,
                 fallback_name="Add electricity charge, kWh [0..500]")
    .tuya_number(dp_id=114, attribute_name="current_threshold", translation_key="current_threshold",
                 type=t.uint32_t, min_value=1, max_value=50, step=1, unit=UnitOfElectricCurrent.AMPERE,
                 fallback_name="Current threshold, A [1..50]")
    .tuya_number(dp_id=115, attribute_name="overvoltage_threshold", translation_key="overvoltage_threshold",
                 type=t.uint32_t, min_value=100, max_value=280, step=1, unit=UnitOfElectricPotential.VOLT,
                 fallback_name="Over-voltage threshold, V [100..280]")
    .tuya_number(dp_id=116, attribute_name="undervoltage_threshold", translation_key="undervoltage_threshold",
                 type=t.uint32_t, min_value=100, max_value=280, step=1, unit=UnitOfElectricPotential.VOLT,
                 fallback_name="Under-voltage threshold, V [100..280]")
    .tuya_number(dp_id=118, attribute_name="temperature_threshold", translation_key="temperature_threshold",
                 type=t.int32s, min_value=-25, max_value=100, step=1, multiplier=0.1, unit=UnitOfTemperature.CELSIUS,
                 fallback_name="Temperature threshold, C [-25..100]")
    # e27182: The two alerts below I was unable to make working / 11.06.2026
    .tuya_number(dp_id=119, attribute_name="overpower_threshold", translation_key="overpower_threshold",
                 type=t.uint32_t, min_value=5, max_value=12005, step=10, unit=UnitOfPower.WATT,
                 fallback_name="Over-power threshold, W [5..12005]")
    .tuya_number(dp_id=120, attribute_name="balance_threshold", translation_key="balance_threshold",
                 type=t.uint32_t, min_value=10, max_value=500, step=1, unit=UnitOfEnergy.KILO_WATT_HOUR,
                 fallback_name="Balance threshold, kWh [10..500]")

    .adds(TuyaElectricalMeasurement)
    .skip_configuration()
    .add_to_registry()
)
