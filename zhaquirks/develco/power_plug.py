"""Develco smart plugs."""

from zigpy.quirks.v2 import (
    EntityType,
    QuirkBuilder,
    SensorDeviceClass,
    SensorStateClass,
    UnitOfTemperature,
)
from zigpy.zcl.clusters.general import DeviceTemperature

(
    QuirkBuilder("frient A/S", "SPLZB-141")
    .applies_to("Develco Products A/S", "SPLZB-131")
    .prevent_default_entity_creation(
        endpoint_id=2, cluster_id=DeviceTemperature.cluster_id
    )
    .sensor(
        attribute_name=DeviceTemperature.AttributeDefs.current_temperature.name,
        cluster_id=DeviceTemperature.cluster_id,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        unit=UnitOfTemperature.CELSIUS,
        divisor=1,  # This should be 100 but the device does not follow the spec
        translation_key="device_temperature",
        fallback_name="Device temperature",
        entity_type=EntityType.DIAGNOSTIC,
        unique_id_suffix="2-2",  # Replace the ZHA entity
    )
    .add_to_registry()
)
