"""HOBEIAN ZG-210Z Pressure Sensing Strap / Bed Occupancy Sensor."""

from zigpy.quirks.v2 import EntityType
from zigpy.quirks.v2.homeassistant import (
    PERCENTAGE,
    UnitOfTemperature,
    UnitOfTime,
)
from zigpy.quirks.v2.homeassistant.number import NumberDeviceClass
from zigpy.quirks.v2.homeassistant.sensor import SensorStateClass
import zigpy.types as t

from zhaquirks.tuya.builder import TuyaQuirkBuilder


class PressureState(t.enum8):
    """Pressure state enum."""

    None_ = 0x00
    Sit = 0x01
    Sedentary = 0x02


(
    TuyaQuirkBuilder("_TZE200_ihizzpzn", "ZG-210Z")
    .tuya_enum(
        dp_id=1,
        attribute_name="pressure_state",
        enum_class=PressureState,
        translation_key="pressure_state",
        fallback_name="Pressure state",
    )
    .tuya_sensor(
        dp_id=2,
        attribute_name="current_pressure",
        type=t.uint32_t,
        state_class=SensorStateClass.MEASUREMENT,
        translation_key="current_pressure",
        fallback_name="Current pressure",
    )
    .tuya_temperature(dp_id=101, scale=10)
    .tuya_humidity(dp_id=102)
    .tuya_battery(dp_id=4)
    .tuya_number(
        dp_id=105,
        attribute_name="pressure_intensity",
        type=t.uint32_t,
        min_value=0,
        max_value=2000,
        step=1,
        entity_type=EntityType.CONFIG,
        translation_key="pressure_intensity",
        fallback_name="Pressure threshold",
    )
    .tuya_number(
        dp_id=106,
        attribute_name="presence_delay",
        type=t.uint32_t,
        device_class=NumberDeviceClass.DURATION,
        unit=UnitOfTime.SECONDS,
        min_value=0,
        max_value=3600,
        step=1,
        entity_type=EntityType.CONFIG,
        translation_key="presence_delay",
        fallback_name="Presence delay",
    )
    .tuya_number(
        dp_id=107,
        attribute_name="sedentary_reminder",
        type=t.uint32_t,
        device_class=NumberDeviceClass.DURATION,
        unit=UnitOfTime.MINUTES,
        min_value=0,
        max_value=1440,
        step=1,
        entity_type=EntityType.CONFIG,
        translation_key="sedentary_reminder",
        fallback_name="Sedentary reminder",
    )
    .tuya_number(
        dp_id=103,
        attribute_name="temperature_calibration",
        type=t.int32s,
        device_class=NumberDeviceClass.TEMPERATURE,
        unit=UnitOfTemperature.CELSIUS,
        min_value=-2.0,
        max_value=2.0,
        step=0.1,
        multiplier=0.1,
        entity_type=EntityType.CONFIG,
        translation_key="temperature_calibration",
        fallback_name="Temperature calibration",
    )
    .tuya_number(
        dp_id=104,
        attribute_name="humidity_calibration",
        type=t.int32s,
        unit=PERCENTAGE,
        min_value=-30,
        max_value=30,
        step=1,
        entity_type=EntityType.CONFIG,
        translation_key="humidity_calibration",
        fallback_name="Humidity calibration",
    )
    .skip_configuration()
    .add_to_registry()
)
