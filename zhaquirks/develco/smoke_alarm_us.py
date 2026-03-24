"""Frient Smoke Alarm US (SCAZB-141)."""

from zigpy.quirks.v2 import QuirkBuilder
from zigpy.quirks.v2.homeassistant import EntityType
from zigpy.quirks.v2.homeassistant.binary_sensor import BinarySensorDeviceClass
from zigpy.zcl.clusters.general import BinaryInput
from zigpy.zcl.clusters.security import IasWd, IasZone

from zhaquirks.develco import DEVELCO, FRIENT, DevelcoIasZone, DevelcoPowerConfiguration
from zhaquirks.quirk_ids import SIREN_BASIC


class DevelcoIasZoneCO(DevelcoIasZone):
    """IAS Zone with zone_type forced to Carbon Monoxide Sensor."""

    # Device reports non-standard zone_type 0x0227
    # We can't use change_entity_metadata with new_device_class, as ZHA
    # currently overrides the device class if any zone_type is set, so we force CO.
    # There is also an issue in ZHA where the new_device_class needs to be provided
    # with strings, not the actual BinarySensorDeviceClass enum member.
    _CONSTANT_ATTRIBUTES = {
        IasZone.AttributeDefs.zone_type.id: IasZone.ZoneType.Carbon_Monoxide_Sensor,
    }


(
    QuirkBuilder(FRIENT, "SCAZB-141")
    .applies_to(DEVELCO, "SCAZB-141")
    .replaces(DevelcoIasZone, endpoint_id=35)
    .replaces(DevelcoIasZoneCO, endpoint_id=46)
    .replaces(DevelcoPowerConfiguration, endpoint_id=35)
    .exposes_feature(SIREN_BASIC)
    # Hide the BinaryInput sensors on both endpoints (duplicated by IAS Zone)
    .prevent_default_entity_creation(
        endpoint_id=35,
        cluster_id=BinaryInput.cluster_id,
    )
    .prevent_default_entity_creation(
        endpoint_id=46,
        cluster_id=BinaryInput.cluster_id,
    )
    # Tamper and test binary sensors from zone_status bits
    .binary_sensor(
        attribute_name=IasZone.AttributeDefs.zone_status.name,
        cluster_id=IasZone.cluster_id,
        endpoint_id=35,
        device_class=BinarySensorDeviceClass.TAMPER,
        attribute_converter=lambda value: bool(value & IasZone.ZoneStatus.Tamper),
        unique_id_suffix="tamper",
        fallback_name="Tamper",
    )
    .binary_sensor(
        attribute_name=IasZone.AttributeDefs.zone_status.name,
        cluster_id=IasZone.cluster_id,
        endpoint_id=35,
        attribute_converter=lambda value: bool(value & IasZone.ZoneStatus.Test),
        unique_id_suffix="test",
        translation_key="test",
        fallback_name="Test",
    )
    # Not the siren
    .change_entity_metadata(
        endpoint_id=35,
        cluster_id=IasWd.cluster_id,
        new_primary=False,
        new_entity_category=EntityType.CONFIG,
    )
    .add_to_registry()
)
