"""Konke temp and humidity sensor."""

from zigpy.quirks.v2 import QuirkBuilder

from zhaquirks import PowerConfigurationCluster
from zhaquirks.konke import KONKE

(
    QuirkBuilder(KONKE, "3AFE140103020000")
    .applies_to(KONKE, "3AFE220103020000")
    .replaces(PowerConfigurationCluster, endpoint_id=1)
    .add_to_registry()
)
