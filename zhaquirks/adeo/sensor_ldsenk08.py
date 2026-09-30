"""Device handler for ADEO Lexman LDSENK08 smart door/window sensor."""

from zigpy.zcl.clusters.security import IasZone

from zhaquirks.builder import BinarySensorDeviceClass, EntityType, QuirkBuilder

(
    QuirkBuilder("ADEO", "LDSENK08")
    # Contact/opening from IAS zone_status Alarm_1 (bit 0).
    .binary_sensor(
        attribute_name=IasZone.AttributeDefs.zone_status.name,
        cluster_id=IasZone.cluster_id,
        device_class=BinarySensorDeviceClass.OPENING,
        attribute_converter=lambda value: bool(value & IasZone.ZoneStatus.Alarm_1),
        unique_id_suffix="contact",
        entity_type=EntityType.STANDARD,
        fallback_name="Contact",
    )
    # Vibration from IAS zone_status Alarm_2 (bit 1).
    .binary_sensor(
        attribute_name=IasZone.AttributeDefs.zone_status.name,
        cluster_id=IasZone.cluster_id,
        device_class=BinarySensorDeviceClass.VIBRATION,
        attribute_converter=lambda value: bool(value & IasZone.ZoneStatus.Alarm_2),
        unique_id_suffix="vibration",
        entity_type=EntityType.STANDARD,
        fallback_name="Vibration",
    )
    # Tamper/manipulation from IAS zone_status Tamper (bit 2).
    .binary_sensor(
        attribute_name=IasZone.AttributeDefs.zone_status.name,
        cluster_id=IasZone.cluster_id,
        device_class=BinarySensorDeviceClass.TAMPER,
        attribute_converter=lambda value: bool(value & IasZone.ZoneStatus.Tamper),
        unique_id_suffix="tamper",
        entity_type=EntityType.STANDARD,
        fallback_name="Tamper",
    )
    # Five levels, matching the vendor gateway (see zigbee2mqtt LDSENK08).
    .number(
        attribute_name=IasZone.AttributeDefs.current_zone_sensitivity_level.name,
        cluster_id=IasZone.cluster_id,
        min_value=0,
        max_value=4,
        step=1,
        translation_key="sensitivity",
        fallback_name="Sensitivity",
    )
    # Prevent ZHA's stock IAS zone binary (unique id …-1-1280). Quirk binaries use
    # -contact / -vibration / -tamper and must not match this suffix.
    .prevent_default_entity_creation(
        endpoint_id=1,
        cluster_id=IasZone.cluster_id,
        unique_id_suffix="-1-1280",
    )
    .add_to_registry()
)
