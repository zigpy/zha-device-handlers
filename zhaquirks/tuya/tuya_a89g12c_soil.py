"""Tuya A89G12C Arteco soil sensor."""

import zigpy.types as t
from zigpy.zcl.clusters.measurement import RelativeHumidity

from zhaquirks.builder import (
    LIGHT_LUX,
    PERCENTAGE,
    EntityType,
    SensorDeviceClass,
    SensorStateClass,
    UnitOfConductivity,
)
from zhaquirks.tuya.builder import TuyaQuirkBuilder

(
    TuyaQuirkBuilder("A89G12C", "Arteco")
    .removes(RelativeHumidity.cluster_id)
    .tuya_sensor(
        dp_id=3,
        attribute_name="soil_moisture",
        type=t.uint8_t,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.MOISTURE,
        entity_type=EntityType.STANDARD,
        unit=PERCENTAGE,
        translation_key="soil_moisture",
        fallback_name="Soil moisture",
    )
    .tuya_sensor(
        dp_id=102,
        attribute_name="illuminance",
        type=t.uint32_t,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.ILLUMINANCE,
        entity_type=EntityType.STANDARD,
        unit=LIGHT_LUX,
        translation_key="illuminance",
        fallback_name="Illuminance",
    )
    .tuya_sensor(
        dp_id=112,
        attribute_name="soil_conductivity",
        type=t.uint16_t,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.CONDUCTIVITY,
        entity_type=EntityType.STANDARD,
        unit=UnitOfConductivity.MICROSIEMENS_PER_CM,
        translation_key="soil_conductivity",
        fallback_name="Soil conductivity",
    )
    .skip_configuration()
    .add_to_registry()
)
