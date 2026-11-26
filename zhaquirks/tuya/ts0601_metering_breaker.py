"""Tuya TS0601 DIN-rail metering reclosing protector / circuit breaker (_TZE284_5m4nchbm)."""

import zigpy.types as t

from zhaquirks.builder import (
    SensorDeviceClass,
    SensorStateClass,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfPower,
    UnitOfTemperature,
)
from zhaquirks.tuya.builder import TuyaQuirkBuilder

(
    TuyaQuirkBuilder("_TZE284_5m4nchbm", "TS0601")
    # DP 1: relay state (bool)
    .tuya_onoff(dp_id=1)
    # DP 20: mains voltage, reported as 2409 for 240.9 V
    .tuya_sensor(
        dp_id=20,
        attribute_name="voltage",
        type=t.uint32_t,
        divisor=10,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        unit=UnitOfElectricPotential.VOLT,
        fallback_name="Voltage",
    )
    # Current scale confirmed against the device display; power and energy scales are unverified.
    .tuya_sensor(
        dp_id=18,
        attribute_name="current",
        type=t.uint32_t,
        divisor=100,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        unit=UnitOfElectricCurrent.AMPERE,
        fallback_name="Current",
    )
    .tuya_sensor(
        dp_id=19,
        attribute_name="power",
        type=t.uint32_t,
        divisor=10,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        unit=UnitOfPower.WATT,
        fallback_name="Power",
    )
    # DP 47 drifts slowly (35-42), consistent with the internal temperature in °C.
    .tuya_sensor(
        dp_id=47,
        attribute_name="temperature",
        type=t.uint32_t,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        unit=UnitOfTemperature.CELSIUS,
        fallback_name="Temperature",
    )
    .skip_configuration()
    .add_to_registry()
)
