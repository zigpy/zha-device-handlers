"""Zemismart SPM01V2 single-phase energy meter."""

from zha.units import (
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfFrequency,
    UnitOfPower,
)
import zigpy.types as t

from zhaquirks.builder import SensorDeviceClass, SensorStateClass
from zhaquirks.tuya.builder import TuyaQuirkBuilder

(
    TuyaQuirkBuilder("_TZE200_qhlxve78", "TS0601")
    .applies_to("_TZE284_qhlxve78", "TS0601")
    .applies_to("_TZE204_qhlxve78", "TS0601")
    # Total forward active energy
    .tuya_sensor(
        dp_id=1,
        attribute_name="energy",
        type=t.uint32_t,
        divisor=100,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        unit=UnitOfEnergy.KILO_WATT_HOUR,
        fallback_name="Energy",
    )
    # Total reverse active energy
    .tuya_sensor(
        dp_id=2,
        attribute_name="produced_energy",
        type=t.uint32_t,
        divisor=100,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        unit=UnitOfEnergy.KILO_WATT_HOUR,
        fallback_name="Produced energy",
    )
    # Power factor: raw value in percent
    .tuya_sensor(
        dp_id=15,
        attribute_name="power_factor",
        type=t.uint32_t,
        device_class=SensorDeviceClass.POWER_FACTOR,
        state_class=SensorStateClass.MEASUREMENT,
        unit="%",
        fallback_name="Power factor",
    )
    # AC frequency
    .tuya_sensor(
        dp_id=101,
        attribute_name="ac_frequency",
        type=t.uint32_t,
        divisor=100,
        device_class=SensorDeviceClass.FREQUENCY,
        state_class=SensorStateClass.MEASUREMENT,
        unit=UnitOfFrequency.HERTZ,
        fallback_name="AC frequency",
    )
    # Voltage
    .tuya_sensor(
        dp_id=102,
        attribute_name="voltage",
        type=t.uint32_t,
        divisor=10,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        unit=UnitOfElectricPotential.VOLT,
        fallback_name="Voltage",
    )
    # Current
    .tuya_sensor(
        dp_id=103,
        attribute_name="current",
        type=t.uint32_t,
        divisor=1000,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        unit=UnitOfElectricCurrent.AMPERE,
        fallback_name="Current",
    )
    # Active power
    .tuya_sensor(
        dp_id=104,
        attribute_name="power",
        type=t.uint32_t,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        unit=UnitOfPower.WATT,
        fallback_name="Power",
    )
    # DP6: Unknown RAW datapoint, intentionally ignored
    .tuya_dp_multi(dp_id=6, attribute_mapping=[])
    .skip_configuration()
    .add_to_registry()
)
