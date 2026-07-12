"""Sonoff SNZB-03P - Zigbee motion sensor."""

from zigpy.zcl.clusters.measurement import OccupancySensing

from zhaquirks.builder import QuirkBuilder

(
    # <SimpleDescriptor endpoint=1, profile=260, device_type=263
    # device_version=1
    # input_clusters=[0, 1, 3, 32, 1030, 1280, 64599]
    # output_clusters=[3, 25]>
    QuirkBuilder("eWeLink", "SNZB-03P")
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
    .add_to_registry()
)
