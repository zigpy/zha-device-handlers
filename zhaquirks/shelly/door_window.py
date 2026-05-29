"""Device handler for Shelly BLU DoorWindow ZB."""

from __future__ import annotations

from zigpy.zcl.clusters.security import IasZone

from zhaquirks.builder import (
    BinarySensorDeviceClass,
    EntityPlatform,
    EntityType,
    QuirkBuilder,
    ReportingConfig,
)
from zhaquirks.shelly import LightLevel, ShellyLightLevelCluster

(
    QuirkBuilder("Shelly", "BLU DoorWindow ZB")
    .replaces(ShellyLightLevelCluster)
    .enum(
        attribute_name=ShellyLightLevelCluster.AttributeDefs.light_level.name,
        enum_class=LightLevel,
        cluster_id=ShellyLightLevelCluster.cluster_id,
        entity_platform=EntityPlatform.SENSOR,
        entity_type=EntityType.STANDARD,
        reporting_config=ReportingConfig(
            min_interval=15, max_interval=300, reportable_change=1
        ),
        translation_key="light_level",
        fallback_name="Light level",
    )
    # Disable the default ZHA IAS Zone entity (unique_id ends with
    # "{endpoint_id}-{cluster_id}") since the Door/Tilt sensors replace it.
    .change_entity_metadata(
        endpoint_id=1,
        cluster_id=IasZone.cluster_id,
        unique_id_suffix=f"1-{IasZone.cluster_id}",
        new_entity_registry_enabled_default=False,
    )
    .binary_sensor(
        attribute_name=IasZone.AttributeDefs.zone_status.name,
        cluster_id=IasZone.cluster_id,
        entity_type=EntityType.STANDARD,
        device_class=BinarySensorDeviceClass.DOOR,
        attribute_converter=lambda value: bool(
            value & (IasZone.ZoneStatus.Alarm_1 | IasZone.ZoneStatus.Alarm_2)
        ),
        fallback_name="Door",
    )
    .binary_sensor(
        attribute_name=IasZone.AttributeDefs.zone_status.name,
        cluster_id=IasZone.cluster_id,
        entity_type=EntityType.STANDARD,
        attribute_converter=lambda value: (
            (value & (IasZone.ZoneStatus.Alarm_1 | IasZone.ZoneStatus.Alarm_2))
            == IasZone.ZoneStatus.Alarm_1
        ),
        unique_id_suffix="tilt",
        translation_key="tilt",
        fallback_name="Tilt",
    )
    .add_to_registry()
)
