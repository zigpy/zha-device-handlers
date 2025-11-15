"""Centralite 3321S quirk."""

# pylint disable=C0103
from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl.clusters.general import PowerConfiguration

from zhaquirks import PowerConfigurationCluster
from zhaquirks.centralite import CENTRALITE, CentraLiteAccelCluster
from zhaquirks.samjin import SAMJIN

(
    QuirkBuilder(CENTRALITE, "3320")
    .applies_to(CENTRALITE, "3321-S")
    .applies_to(CENTRALITE, "3321")
    .applies_to(SAMJIN, "multi")
    .replaces(PowerConfigurationCluster, endpoint_id=1)
    .replaces(CentraLiteAccelCluster, endpoint_id=1)
    .removes(PowerConfiguration.cluster_id, endpoint_id=2)
    .add_to_registry()
)
