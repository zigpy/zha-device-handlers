"""Quirks v2 for Tuya vibration sensor with accelerometer data (_TZE200_iba1ckek)."""

from zhaquirks.tuya.builder import TuyaQuirkBuilder
from zigpy.quirks.v2.homeassistant import EntityPlatform, EntityType
from zigpy.quirks.v2.homeassistant.sensor import SensorDeviceClass, SensorStateClass
from zigpy.quirks.v2.homeassistant.number import NumberDeviceClass
import zigpy.types as t


def uint_to_sint(value: t.uint8_t) -> t.int8s:
    if value > 127:
      value = value - 256
    return value


def acceleration_to_degrees(raw_value):
    """Convert raw acceleration value to tilt angle in degrees.
    
    Assumes raw values represent acceleration in units where:
    - 127 = +1G (90 degrees tilt)
    - -128 = -1G (-90 degrees tilt)
    - 0 = 0G (0 degrees tilt)
    """
    
    # Convert to G-force (assuming range is roughly -1G to +1G)
    # Scale factor: 127 raw units = 1G
    g_force = raw_value / 255.0
    
    # Clamp to valid range for arcsin [-1, 1]
    g_force = max(-1.0, min(1.0, g_force))
    
    # Convert to degrees using arcsin
    angle_radians = math.asin(g_force)
    angle_degrees = math.degrees(angle_radians)
    
    return round(angle_degrees, 1)

# Create the v2 quirk using the fluent interface
(
    TuyaQuirkBuilder("_TZE200_iba1ckek", "TS0601")
    .skip_configuration()
    # Acceleration sensors (raw values 0..255)
    .tuya_sensor(
	dp_id=101,
	attribute_name="x_axis",
	type=t.uint8_t,
	state_class=SensorStateClass.MEASUREMENT,
	device_class=SensorDeviceClass.ACCELERATION,
	entity_type=EntityType.STANDARD,
	translation_key="x_axis_acceleration",
	fallback_name="X-axis Acceleration",
        converter=uint_to_sint,
    )
    .tuya_sensor(
	dp_id=102,
	attribute_name="y_axis",
	type=t.uint8_t,
	state_class=SensorStateClass.MEASUREMENT,
	device_class=SensorDeviceClass.ACCELERATION,
	entity_type=EntityType.STANDARD,
	translation_key="y_axis_acceleration",
	fallback_name="Y-axis Acceleration",
        converter=uint_to_sint,
    )
    .tuya_sensor(
	dp_id=103,
	attribute_name="z_axis",
	type=t.uint8_t,
	state_class=SensorStateClass.MEASUREMENT,
	device_class=SensorDeviceClass.ACCELERATION,
	entity_type=EntityType.STANDARD,
	translation_key="z_axis_acceleration",
	fallback_name="Z-axis Acceleration",
        converter=uint_to_sint,
    )

    # Tilt angle sensors (in degrees)
    #.tuya_sensor(
    #    dp_id=101,
    #    attribute_name="x_tilt",
    #    type=t.Half,
    #    converter=acceleration_to_degrees,
    #    state_class=SensorStateClass.MEASUREMENT,
    #    entity_type=EntityType.STANDARD,
    #    translation_key="x_axis_tilt",
    #    fallback_name="X-axis Tilt Angle",
    #    unit="°",
    #)
    #.tuya_sensor(
    #    dp_id=102,
    #    attribute_name="y_tilt", 
    #    type=t.Half,
    #    converter=acceleration_to_degrees,
    #    state_class=SensorStateClass.MEASUREMENT,
    #    entity_type=EntityType.STANDARD,
    #    translation_key="y_axis_tilt",
    #    fallback_name="Y-axis Tilt Angle",
    #    unit="°",
    #)
    #.tuya_sensor(
    #    dp_id=103,
    #    attribute_name="z_tilt",
    #    type=t.Half,
    #    converter=acceleration_to_degrees,
    #    state_class=SensorStateClass.MEASUREMENT,
    #    entity_type=EntityType.STANDARD,
    #    translation_key="z_axis_tilt",
    #    fallback_name="Z-axis Tilt Angle", 
    #    unit="°",
    #)

    .add_to_registry()
)

