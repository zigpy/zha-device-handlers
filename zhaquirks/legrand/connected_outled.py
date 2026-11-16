"""Module for Legrand switches (without dimming functionality)."""

from zigpy.zcl import ClusterType
from zigpy.zcl.clusters.general import BinaryInput, OnOff

from zhaquirks.builder import EntityFilter, QuirkBuilder
from zhaquirks.legrand import LEGRAND, LegrandCluster, LegrandIdentify

(
    QuirkBuilder(f" {LEGRAND}", " Connected outlet")
    .replaces(LegrandCluster)
    .replaces(LegrandIdentify)
    .prevent_default_entity_creation(endpoint_id=1, cluster_id=BinaryInput.cluster_id)
    .removes_entity(
        EntityFilter(
            endpoint_id=1,
            cluster_id=OnOff.cluster_id,
            cluster_type=ClusterType.Client,
        )
    )
    .switch(
        attribute_name=LegrandCluster.AttributeDefs.led_dark.name,
        cluster_id=LegrandCluster.cluster_id,
        translation_key="turn_on_led_when_off",
        fallback_name="Turn on LED when off",
    )
    .switch(
        attribute_name=LegrandCluster.AttributeDefs.led_on.name,
        cluster_id=LegrandCluster.cluster_id,
        translation_key="turn_on_led_when_on",
        fallback_name="Turn on LED when on",
    )
    .add_to_registry()
)
