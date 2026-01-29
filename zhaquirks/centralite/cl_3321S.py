"""Centralite 3321S quirk."""

# pylint disable=C0103
from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl.clusters.general import PowerConfiguration

from zhaquirks import PowerConfigurationCluster
from zhaquirks.centralite import CENTRALITE, CentraLiteAccelCluster

(
    QuirkBuilder(CENTRALITE, "3320")
    .applies_to(CENTRALITE, "3321-S")
    .applies_to(CENTRALITE, "3321")
    .replaces(PowerConfigurationCluster, endpoint_id=1)
    .replaces(CentraLiteAccelCluster, endpoint_id=1)
    .removes(PowerConfiguration, endpoint_id=2)
    .add_to_registry()
)
