"""Nous E10 CO2, Temperature, and Humidity Detector.

Manufacturer: _TZE284_xpvamyfz
Model: TS0601
"""

from zigpy.quirks.v2.homeassistant.sensor import SensorDeviceClass, SensorStateClass
import zigpy.types as t

from zhaquirks.tuya.builder import TuyaQuirkBuilder

(
    TuyaQuirkBuilder("_TZE284_xpvamyfz", "TS0601")
    .tuya_sensor(
        dp_id=2,
        attribute_name="carbon_dioxide_concentration",
        type=t.uint32_t,
        divisor=1,
        device_class=SensorDeviceClass.CO2,
        state_class=SensorStateClass.MEASUREMENT,
        unit="ppm",
        fallback_name="CO2",
    )
    .tuya_sensor(
        dp_id=18,
        attribute_name="temperature",
        type=t.int32s,
        divisor=1,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        unit="°C",
        fallback_name="Temperature",
    )
    .tuya_sensor(
        dp_id=19,
        attribute_name="humidity",
        type=t.uint32_t,
        divisor=1,
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
        unit="%",
        fallback_name="Humidity",
    )
    .skip_configuration()
    .add_to_registry()
)
