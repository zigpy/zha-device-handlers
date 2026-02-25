"""frient Motion Sensor/Pro/PET."""

from zigpy.quirks.v2 import BinarySensorDeviceClass, QuirkBuilder
from zigpy.zcl.clusters.general import BinaryInput
from zigpy.zcl.clusters.security import IasZone

from zhaquirks.develco import DEVELCO, FRIENT, DevelcoIasZone, DevelcoPowerConfiguration

# MOSZB-140 (Motion Sensor Pro) - has tamper sensor, no sensitivity levels
(
    QuirkBuilder(FRIENT, "MOSZB-140")
    .applies_to(DEVELCO, "MOSZB-140")
    .replaces(DevelcoPowerConfiguration, endpoint_id=35)
    .replaces(DevelcoIasZone, endpoint_id=35)
    .binary_sensor(
        attribute_name=IasZone.AttributeDefs.zone_status.name,
        cluster_id=IasZone.cluster_id,
        endpoint_id=35,
        device_class=BinarySensorDeviceClass.TAMPER,
        attribute_converter=lambda value: bool(value & IasZone.ZoneStatus.Tamper),
        unique_id_suffix="tamper",
        fallback_name="Tamper",
    )
    # This entity does not do anything
    .prevent_default_entity_creation(endpoint_id=35, cluster_id=BinaryInput.cluster_id)
    # These endpoints are duplicates of 35 and do not create useful entities
    .prevent_default_entity_creation(endpoint_id=40)
    .prevent_default_entity_creation(endpoint_id=41)
    .add_to_registry()
)

# MOSZB-141 (Motion Sensor) - no tamper sensor, no sensitivity levels
(
    QuirkBuilder(FRIENT, "MOSZB-141")
    .applies_to(DEVELCO, "MOSZB-141")
    .replaces(DevelcoPowerConfiguration, endpoint_id=35)
    .replaces(DevelcoIasZone, endpoint_id=35)
    # This entity does not do anything
    .prevent_default_entity_creation(endpoint_id=35, cluster_id=BinaryInput.cluster_id)
    # These endpoints are duplicates of 35 and do not create useful entities
    .prevent_default_entity_creation(endpoint_id=40)
    .prevent_default_entity_creation(endpoint_id=41)
    .add_to_registry()
)

# MOSZB-153 (Motion Sensor 2 PET) - no tamper sensor, but has sensitivity levels
(
    QuirkBuilder(FRIENT, "MOSZB-153")
    .replaces(DevelcoPowerConfiguration, endpoint_id=35)
    .replaces(DevelcoIasZone, endpoint_id=35)
    .number(
        attribute_name=IasZone.AttributeDefs.current_zone_sensitivity_level.name,
        cluster_id=IasZone.cluster_id,
        endpoint_id=35,
        min_value=1,
        max_value=4,
        step=1,
        translation_key="sensitivity_level",
        fallback_name="Sensitivity level",
    )
    # This entity does not do anything
    .prevent_default_entity_creation(endpoint_id=35, cluster_id=BinaryInput.cluster_id)
    # These endpoints are duplicates of 35 and do not create useful entities
    .prevent_default_entity_creation(endpoint_id=40)
    .prevent_default_entity_creation(endpoint_id=41)
    .add_to_registry()
)
