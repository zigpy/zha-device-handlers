"""Sonoff SNZB-06P - Zigbee presence sensor."""

import zigpy.types as t
from zigpy.zcl.clusters.measurement import OccupancySensing
from zigpy.zcl.clusters.security import IasZone
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef

from zhaquirks.builder import EntityPlatform, EntityType, QuirkBuilder
from zhaquirks.clusters import CustomCluster


class IlluminationStatus(t.enum8):
    """Last measured state of illumination enum."""

    Dark = 0x00
    Light = 0x01


class PresenceDetectionSensitivity(t.enum8):
    """Presence detection sensitivity enum."""

    Low = 0x01
    Medium = 0x02
    High = 0x03


class SonoffFC11Cluster(CustomCluster):
    """Sonoff manufacturer specific cluster that provides illuminance."""

    cluster_id = 0xFC11
    ep_attribute = "sonoff_manufacturer"

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        last_illumination_state = ZCLAttributeDef(
            id=0x2001,
            type=IlluminationStatus,
        )


(
    # <SimpleDescriptor endpoint=1, profile=260, device_type=263
    # device_version=1
    # input_clusters=[0, 3, 1030, 1280, 64599, 64529]
    # output_clusters=[3, 25]>
    QuirkBuilder("SONOFF", "SNZB-06P")
    .removes(IasZone.cluster_id)
    .replaces(SonoffFC11Cluster)
    .number(
        attribute_name=OccupancySensing.AttributeDefs.ultrasonic_o_to_u_delay.name,
        cluster_id=OccupancySensing.cluster_id,
        min_value=15,
        max_value=60,
        step=1,
        mode="box",
        # keep the unique ID of the previous ZHA-native entity
        unique_id_suffix="1030-presence_detection_timeout",
        translation_key="presence_detection_timeout",
        fallback_name="Presence detection timeout",
    )
    .enum(
        attribute_name=OccupancySensing.AttributeDefs.ultrasonic_u_to_o_threshold.name,
        enum_class=PresenceDetectionSensitivity,
        cluster_id=OccupancySensing.cluster_id,
        # keep the unique ID of the previous ZHA-native entity
        unique_id_suffix="1030-detection_sensitivity",
        translation_key="detection_sensitivity",
        fallback_name="Detection sensitivity",
    )
    .enum(
        attribute_name=SonoffFC11Cluster.AttributeDefs.last_illumination_state.name,
        enum_class=IlluminationStatus,
        cluster_id=SonoffFC11Cluster.cluster_id,
        entity_platform=EntityPlatform.SENSOR,
        entity_type=EntityType.STANDARD,
        # keep the unique ID of the previous ZHA-native entity
        unique_id_suffix="64529-last_illumination",
        translation_key="last_illumination_state",
        fallback_name="Last illumination state",
    )
    .add_to_registry()
)
