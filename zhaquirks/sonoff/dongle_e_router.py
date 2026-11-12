"""SONOFF ZBDongle-E Zigbee router quirk."""

from zigpy.zcl.clusters.general import LevelControl, OnOff
from zigpy.zcl.clusters.lighting import Color

from zhaquirks.builder import QuirkBuilder

(
    QuirkBuilder("SONOFF", "DONGLE-E_R")
    .prevent_default_entity_creation(
        endpoint_id=1,
        cluster_id=OnOff.cluster_id,
    )
    .prevent_default_entity_creation(
        endpoint_id=1,
        cluster_id=LevelControl.cluster_id,
    )
    .prevent_default_entity_creation(
        endpoint_id=2,
        cluster_id=OnOff.cluster_id,
    )
    .prevent_default_entity_creation(
        endpoint_id=2,
        cluster_id=LevelControl.cluster_id,
    )
    .prevent_default_entity_creation(
        endpoint_id=2,
        cluster_id=Color.cluster_id,
    )
    .add_to_registry()
)
