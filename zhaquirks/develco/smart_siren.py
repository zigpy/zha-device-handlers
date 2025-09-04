"""Smart siren."""

from zigpy.quirks.v2 import (
    EntityType,
    QuirkBuilder,
    SensorDeviceClass,
    SensorStateClass,
)
from zigpy.quirks.v2.homeassistant import PERCENTAGE
from zigpy.quirks.v2.homeassistant.binary_sensor import BinarySensorDeviceClass
from zigpy.zcl.clusters.general import PowerConfiguration
from zigpy.zcl.clusters.security import IasZone

BASE_SIREN_QUIRK = (
    QuirkBuilder()
    # Hide the default `ias_zone` entity
    .prevent_default_entity_creation(
        endpoint_id=43,
        cluster_id=IasZone.cluster_id,
        function=lambda entity: entity.translation_key == "ias_zone",
    )
    # This is a mains-powered device that has a backup battery
    .sensor(
        attribute_name=PowerConfiguration.AttributeDefs.battery_percentage_remaining.name,
        cluster_id=PowerConfiguration.cluster_id,
        endpoint_id=43,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        unit=PERCENTAGE,
        divisor=2,  # ZCL reports battery in units of 0.5%, so 200 => 100%
        fallback_name="Battery",
        unique_id_suffix="battery",
        entity_type=EntityType.DIAGNOSTIC,
    )
)

(
    # Device with tamper
    BASE_SIREN_QUIRK.clone()
    .applies_to("frient A/S", "SIRZB-110")
    # Create a tamper sensor
    .binary_sensor(
        endpoint_id=43,
        cluster_id=IasZone.cluster_id,
        attribute_name=IasZone.AttributeDefs.zone_status.name,
        device_class=BinarySensorDeviceClass.TAMPER,
        attribute_converter=lambda value: bool(value & IasZone.ZoneStatus.Tamper),
        unique_id_suffix="tamper",
        fallback_name="Tamper",
    )
    .add_to_registry()
)

(
    # Device without tamper
    BASE_SIREN_QUIRK.clone().applies_to("frient A/S", "SIRZB-111").add_to_registry()
)
