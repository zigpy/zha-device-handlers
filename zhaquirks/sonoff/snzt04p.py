"""Sonoff SNZT-04P contact sensor."""

from zigpy.quirks.v2 import BinarySensorDeviceClass, EntityType, QuirkBuilder
from zigpy.zcl.clusters.security import IasZone

(
    QuirkBuilder("SONOFF", "SNZT-04P")
    .binary_sensor(
        attribute_name=IasZone.AttributeDefs.zone_status.name,
        cluster_id=IasZone.cluster_id,
        endpoint_id=1,
        device_class=BinarySensorDeviceClass.TAMPER,
        attribute_converter=lambda value: bool(value & IasZone.ZoneStatus.Tamper),
        unique_id_suffix="tamper",
        entity_type=EntityType.DIAGNOSTIC,
        fallback_name="Tamper",
    )
    .add_to_registry()
)
