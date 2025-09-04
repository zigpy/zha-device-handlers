"""Develco Motion Sensor Pro."""

from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl.clusters.general import BinaryInput

from zhaquirks.develco import DEVELCO, FRIENT, DevelcoIasZone, DevelcoPowerConfiguration

(
    QuirkBuilder("frient A/S", "MOSZB-153")
    .applies_to(DEVELCO, "MOSZB-140")
    .applies_to(FRIENT, "MOSZB-140")
    .replaces(DevelcoPowerConfiguration, endpoint_id=35)
    .replaces(DevelcoIasZone, endpoint_id=35)
    # This entity does not do anything
    .prevent_default_entity_creation(endpoint_id=35, cluster_id=BinaryInput.cluster_id)
    # This endpoint holds only an occupancy cluster that updates unusably slowly
    .prevent_default_entity_creation(endpoint_id=34)
    # These endpoints are duplicates of 35 and do not create useful entities
    .prevent_default_entity_creation(endpoint_id=40)
    .prevent_default_entity_creation(endpoint_id=41)
    .add_to_registry()
)
