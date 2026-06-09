"""Konke magnet sensor."""

from zigpy.quirks.v2 import QuirkBuilder

from zhaquirks import PowerConfigurationCluster
from zhaquirks.konke import KONKE

(
    QuirkBuilder(KONKE, "3AFE270104020015")
    .applies_to(KONKE, "3AFE280104020015")
    .applies_to(KONKE, "3AFE130104020015")
    .applies_to(KONKE, "3AFE140104020015")
    .replaces(PowerConfigurationCluster, endpoint_id=1)
    .add_to_registry()
)
