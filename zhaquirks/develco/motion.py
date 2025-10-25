"""frient Motion Sensor/Pro/PET."""

from typing import Final

import zigpy.types as t
from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
from zigpy.types import uint16_t
from zigpy.zcl.clusters.general import BinaryInput
from zigpy.zcl.clusters.measurement import OccupancySensing
from zigpy.zcl.clusters.security import IasZone
from zigpy.zcl.foundation import ZCLAttributeDef

from zhaquirks.develco import DEVELCO, FRIENT, DevelcoIasZone, DevelcoPowerConfiguration


class FrientOccupancySensing(CustomCluster, OccupancySensing):
    """Custom occupancy sensing cluster for frient motion sensors."""
    
    class AttributeDefs(OccupancySensing.AttributeDefs):
        """Attribute definitions."""
        
        pir_o_to_u_delay: Final = ZCLAttributeDef(
            id=0x0010,
            type=uint16_t,
            access="rw",
        )

        pir_u_to_o_delay: Final = ZCLAttributeDef(
            id=0x0011,
            type=uint16_t,
            access="rw",
        )


class FrientIasZone(DevelcoIasZone):
    """Custom IAS Zone cluster for frient motion sensors with tamper support."""

    def _update_attribute(self, attrid, value):
        super()._update_attribute(attrid, value)
        if attrid == self.AttributeDefs.zone_status.id:
            # Update tamper state from zone_status bit 2
            tamper_state = bool(value & 0b00000100)
            super()._update_attribute(self.AttributeDefs.tamper.id, tamper_state)

    class AttributeDefs(DevelcoIasZone.AttributeDefs):
        """Attribute definitions."""
        
        tamper: Final = ZCLAttributeDef(
            id=0xFFF2,  # Custom attribute ID
            type=t.Bool,
        )


class FrientPETIasZone(DevelcoIasZone):
    """Custom IAS Zone cluster for frient PET motion sensor with sensitivity levels."""

    class AttributeDefs(DevelcoIasZone.AttributeDefs):
        """Attribute definitions."""
        
        number_of_zone_sensitivity_levels_supported: Final = ZCLAttributeDef(
            id=0x0012,
            type=t.uint8_t,
            access="r",
        )
        
        current_zone_sensitivity_level: Final = ZCLAttributeDef(
            id=0x0013,
            type=t.uint8_t,
            access="rw",
        )


# MOSZB-140 (Motion Sensor Pro) - has tamper sensor, no sensitivity levels
(
    QuirkBuilder(FRIENT, "MOSZB-140")
    .applies_to(DEVELCO, "MOSZB-140")
    .replaces(DevelcoPowerConfiguration, endpoint_id=35)
    .replaces(FrientIasZone, endpoint_id=35)
    .replaces(FrientOccupancySensing, cluster_id=OccupancySensing.cluster_id, endpoint_id=34)
    .binary_sensor(
        attribute_name="tamper",
        cluster_id=IasZone.cluster_id,
        endpoint_id=35,
        entity_type="tamper",
        translation_key="tamper",
        fallback_name="Tamper",
    )
    .number(
        attribute_name="pir_o_to_u_delay",
        cluster_id=OccupancySensing.cluster_id,
        endpoint_id=34,
        min_value=0,
        max_value=65535,
        step=1,
        translation_key="occupancy_delay",
        fallback_name="Occupied to Unoccupied Delay (seconds)",
    )
    .number(
        attribute_name="pir_u_to_o_delay",
        cluster_id=OccupancySensing.cluster_id,
        endpoint_id=34,
        min_value=0,
        max_value=65535,
        step=1,
        translation_key="unoccupancy_delay",
        fallback_name="Unoccupied to Occupied Delay (seconds)",
    )
    .prevent_default_entity_creation(endpoint_id=35, cluster_id=BinaryInput.cluster_id)
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
    .replaces(FrientOccupancySensing, cluster_id=OccupancySensing.cluster_id, endpoint_id=34)
    .number(
        attribute_name="pir_o_to_u_delay",
        cluster_id=OccupancySensing.cluster_id,
        endpoint_id=34,
        min_value=0,
        max_value=65535,
        step=1,
        translation_key="occupancy_delay",
        fallback_name="Occupied to Unoccupied Delay (seconds)",
    )
    .number(
        attribute_name="pir_u_to_o_delay",
        cluster_id=OccupancySensing.cluster_id,
        endpoint_id=34,
        min_value=0,
        max_value=65535,
        step=1,
        translation_key="unoccupancy_delay",
        fallback_name="Unoccupied to Occupied Delay (seconds)",
    )
    .prevent_default_entity_creation(endpoint_id=35, cluster_id=BinaryInput.cluster_id)
    .prevent_default_entity_creation(endpoint_id=40)
    .prevent_default_entity_creation(endpoint_id=41)
    .add_to_registry()
)

# MOSZB-153 (Motion Sensor 2 PET) - no tamper sensor, but has sensitivity levels
(
    QuirkBuilder(FRIENT, "MOSZB-153")
    .replaces(DevelcoPowerConfiguration, endpoint_id=35)
    .replaces(FrientPETIasZone, endpoint_id=35)
    .replaces(FrientOccupancySensing, cluster_id=OccupancySensing.cluster_id, endpoint_id=34)
    .number(
        attribute_name="current_zone_sensitivity_level",
        cluster_id=IasZone.cluster_id,
        endpoint_id=35,
        min_value=0,
        max_value=4,
        step=1,
        translation_key="sensitivity_level",
        fallback_name="Sensitivity Level (0-4)",
    )
    .number(
        attribute_name="pir_o_to_u_delay",
        cluster_id=OccupancySensing.cluster_id,
        endpoint_id=34,
        min_value=0,
        max_value=65535,
        step=1,
        translation_key="occupancy_delay",
        fallback_name="Occupied to Unoccupied Delay (seconds)",
    )
    .number(
        attribute_name="pir_u_to_o_delay",
        cluster_id=OccupancySensing.cluster_id,
        endpoint_id=34,
        min_value=0,
        max_value=65535,
        step=1,
        translation_key="unoccupancy_delay",
        fallback_name="Unoccupied to Occupied Delay (seconds)",
    )
    .sensor(
        attribute_name="number_of_zone_sensitivity_levels_supported",
        cluster_id=IasZone.cluster_id,
        endpoint_id=35,
        translation_key="sensitivity_levels_supported",
        fallback_name="Sensitivity Levels Supported",
    )
    .prevent_default_entity_creation(endpoint_id=35, cluster_id=BinaryInput.cluster_id)
    .prevent_default_entity_creation(endpoint_id=40)
    .prevent_default_entity_creation(endpoint_id=41)
    .add_to_registry()
)
