"""Namron switches and relays."""

from zigpy.zcl.clusters.general import DeviceTemperature

from zhaquirks.builder import (
    EntityType,
    QuirkBuilder,
    SensorDeviceClass,
    SensorStateClass,
    UnitOfTemperature,
)

(
    QuirkBuilder("Namron AS", "4512785")
    # The device reports current_temperature in units of 0.1 °C, violating the
    # ZCL spec (whole degrees, range -200..200). Replace the default entity with
    # one that applies the correct divisor.
    .prevent_default_entity_creation(
        endpoint_id=1,
        cluster_id=DeviceTemperature.cluster_id,
        function=lambda entity: entity.__class__.__name__ == "DeviceTemperature",
    )
    .sensor(
        endpoint_id=1,
        cluster_id=DeviceTemperature.cluster_id,
        attribute_name=DeviceTemperature.AttributeDefs.current_temperature.name,
        divisor=10,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        unit=UnitOfTemperature.CELSIUS,
        entity_type=EntityType.DIAGNOSTIC,
        unique_id_suffix="2",  # Replace the ZHA-native entity ({ieee}-1-2)
        translation_key="device_temperature",
        fallback_name="Device temperature",
    )
    .add_to_registry()
)
