"""Device handler for Shelly BLU H&T Display ZB."""

from __future__ import annotations

from zhaquirks.builder import EntityPlatform, EntityType, QuirkBuilder, ReportingConfig
from zhaquirks.shelly import LightLevel, ShellyLightLevelCluster

(
    QuirkBuilder("Shelly", "BLU H&T Display ZB")
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
    .add_to_registry()
)
