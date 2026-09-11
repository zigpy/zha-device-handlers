"""SONOFF Dongle-LMG21 Zigbee router quirk."""

from zigpy.zcl.clusters.general import LevelControl, OnOff

from zhaquirks.builder import QuirkBuilder

(
    QuirkBuilder("SONOFF", "Dongle-LMG21_ZBRouter")
    .prevent_default_entity_creation(
        endpoint_id=1,
        cluster_id=OnOff.cluster_id,
    )
    .prevent_default_entity_creation(
        endpoint_id=1,
        cluster_id=LevelControl.cluster_id,
    )
    .add_to_registry()
)
