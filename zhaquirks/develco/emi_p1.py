"""Frient Electricity Meter Interface P1 variant."""

from zigpy.quirks.v2 import QuirkBuilder

from zhaquirks import PowerConfigurationCluster

(
    QuirkBuilder("frient A/S", "EMIZB-151")
    # These endpoints are duplicates and completely broken: each one is a "mirror" of
    # endpoint 2 and will set up duplicate attribute reporting for every attribute, the
    # attribute reports will instead be emitted from endpoint 2!
    .prevent_default_entity_creation(endpoint_id=64)
    .prevent_default_entity_creation(endpoint_id=65)
    .prevent_default_entity_creation(endpoint_id=66)
    .prevent_default_entity_creation(endpoint_id=67)
    # No need for battery entity as the device is powered from the meter.
    .prevent_default_entity_creation(
        endpoint_id=2,
        cluster_id=PowerConfigurationCluster.cluster_id,
    )
    .add_to_registry()
)
