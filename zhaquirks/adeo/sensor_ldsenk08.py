"""Device handler for ADEO Lexman LDSENK08 smart door/window sensor."""

from zigpy.zcl.clusters.security import IasZone

from zhaquirks.builder import BinarySensorDeviceClass, EntityType, QuirkBuilder

(
    QuirkBuilder("ADEO", "LDSENK08")
    # Remove the default ZHA IAS Zone entity, so the Contact sensor below can take
    # over its unique id. The function filter is required: the rule would otherwise
    # also match the Contact sensor itself, since that now ends in the same suffix.
    .prevent_default_entity_creation(
        endpoint_id=1,
        cluster_id=IasZone.cluster_id,
        function=lambda entity: entity.__class__.__name__ == "IASZone",
    )
    # Contact/opening from IAS zone_status Alarm_1 (bit 0).
    .binary_sensor(
        attribute_name=IasZone.AttributeDefs.zone_status.name,
        cluster_id=IasZone.cluster_id,
        device_class=BinarySensorDeviceClass.OPENING,
        attribute_converter=lambda value: bool(value & IasZone.ZoneStatus.Alarm_1),
        # Reuse the default IAS Zone entity's unique id ("{ieee}-1-1280"), so existing
        # users keep their entity id and history.
        unique_id_suffix=str(IasZone.cluster_id),
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
    .add_to_registry()
)
