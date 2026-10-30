"""Tuya TS0601 Pressure and Temperature Sensor (_TZE204_w2vunxzm)."""

from zigpy.quirks.v2.homeassistant.sensor import SensorDeviceClass, SensorStateClass
import zigpy.types as t

from zhaquirks.tuya.builder import TuyaQuirkBuilder

(
    TuyaQuirkBuilder("_TZE204_w2vunxzm", "TS0601")
    # Temperature: DP 8, raw value is centidegrees (e.g., 2294 = 22.94°C)
    .tuya_sensor(
        dp_id=8,
        attribute_name="temperature",
        type=t.int32s,
        divisor=100,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        unit="°C",
        translation_key="temperature",
        fallback_name="Temperature",
    )
    # Pressure: DP 101, raw value is decipascals (e.g., 9928 = 992.8 hPa)
    .tuya_sensor(
        dp_id=101,
        attribute_name="atmospheric_pressure",
        type=t.uint32_t,
        divisor=10,
        device_class=SensorDeviceClass.ATMOSPHERIC_PRESSURE,
        state_class=SensorStateClass.MEASUREMENT,
        unit="hPa",
        translation_key="atmospheric_pressure",
        fallback_name="Atmospheric Pressure",
    )
    .skip_configuration()
    .add_to_registry()
)
