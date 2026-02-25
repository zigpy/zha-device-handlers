"""frient Motion Sensor/Pro/PET."""

from typing import Final

from zigpy.quirks.v2 import BinarySensorDeviceClass, QuirkBuilder
import zigpy.types as t
from zigpy.zcl.clusters.general import BinaryInput
from zigpy.zcl.clusters.security import IasZone
from zigpy.zcl.foundation import ZCLAttributeDef

from zhaquirks.develco import DEVELCO, FRIENT, DevelcoIasZone, DevelcoPowerConfiguration


class FrientPETSensitivityIasZone(DevelcoIasZone):
    """Custom IAS Zone cluster for frient PET motion sensor with sensitivity levels."""

    class AttributeDefs(IasZone.AttributeDefs):
        """Attribute definitions."""

        number_of_zone_sensitivity_levels_supported: Final = ZCLAttributeDef(
            id=0x0012,
            type=t.uint8_t,
            access="r",
            manufacturer_code=None,
        )

        current_zone_sensitivity_level: Final = ZCLAttributeDef(
            id=0x0013,
            type=t.uint8_t,
            access="rw",
            manufacturer_code=None,
        )


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
    .replaces(FrientPETSensitivityIasZone, endpoint_id=35)
    .number(
        attribute_name="current_zone_sensitivity_level",
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
