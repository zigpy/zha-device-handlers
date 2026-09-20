"""Intelligent keypad."""

from zigpy.zcl.clusters.general import BinaryInput
from zigpy.zcl.clusters.security import IasWd, IasZone

from zhaquirks.builder import BinarySensorDeviceClass, QuirkBuilder

(
    QuirkBuilder("frient A/S", "KEPZB-110")
    .prevent_default_entity_creation(endpoint_id=44, cluster_id=BinaryInput.cluster_id)
    # Hide the default `ias_zone` entity
    .prevent_default_entity_creation(
        endpoint_id=44,
        cluster_id=IasZone.cluster_id,
        function=lambda entity: entity.translation_key == "ias_zone",
    )
    .prevent_default_entity_creation(
        endpoint_id=44,
        cluster_id=IasWd.cluster_id,
        function=lambda entity: (
            entity.translation_key
            in (
                "default_siren_tone",
                "default_siren_level",
                "default_strobe_level",
                "default_strobe",
            )
        ),
    )
    .binary_sensor(
        endpoint_id=44,
        cluster_id=IasZone.cluster_id,
        attribute_name=IasZone.AttributeDefs.zone_status.name,
        device_class=BinarySensorDeviceClass.TAMPER,
        attribute_converter=lambda value: bool(value & IasZone.ZoneStatus.Tamper),
        unique_id_suffix="tamper",
        fallback_name="Tamper",
    )
    .add_to_registry()
)
