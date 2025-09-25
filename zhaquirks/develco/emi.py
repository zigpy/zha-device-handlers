"""Frient Electricity Meter Interface."""

from zigpy.quirks.v2 import QuirkBuilder

(
    QuirkBuilder("frient A/S", "EMIZB-151")
    # These endpoints are duplicates and completely broken: each one is a "mirror" of
    # endpoint 2 and will set up duplicate attribute reporting for every attribute, the
    # attribute reports will instead be emitted from endpoint 2!
    .prevent_default_entity_creation(endpoint_id=64)
    .prevent_default_entity_creation(endpoint_id=65)
    .prevent_default_entity_creation(endpoint_id=66)
    .prevent_default_entity_creation(endpoint_id=67)
    .add_to_registry()
)
