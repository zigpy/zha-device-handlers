"""Quirk for Aqara D1 Wall Switch (lumi.switch.n3acn3) for Power & Energy Telemetry."""

from zhaquirks.builder import QuirkBuilder
from zhaquirks.xiaomi import (
    LUMI,
    ElectricalMeasurementCluster,
    MeteringCluster,
    XiaomiAqaraE1Cluster,
)

(
    QuirkBuilder(LUMI, "lumi.switch.n3acn3")
    .applies_to("Aqara", "lumi.switch.n3acn3")
    .friendly_name(
        model="Smart wall switch D1 (with neutral, triple rocker)",
        manufacturer="Aqara",
    )
    .replaces(XiaomiAqaraE1Cluster, endpoint_id=1)
    .adds(ElectricalMeasurementCluster, endpoint_id=1)
    .adds(MeteringCluster, endpoint_id=1)
    .add_to_registry()
)
