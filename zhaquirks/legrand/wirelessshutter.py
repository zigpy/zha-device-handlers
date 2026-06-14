"""Module for Legrand remote wireless shutter switches."""

from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl.clusters.general import BinaryInput

from zhaquirks.legrand import LEGRAND, LegrandPowerConfigurationCluster

(
    QuirkBuilder(f" {LEGRAND}", " Shutters central remote switch")
    .replaces(LegrandPowerConfigurationCluster)
    .prevent_default_entity_creation(endpoint_id=1, cluster_id=BinaryInput.cluster_id)
    .add_to_registry()
)
