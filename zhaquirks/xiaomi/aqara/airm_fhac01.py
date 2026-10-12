"""Quirk for LUMI lumi.airm.fhac01 air quality monitor."""

from zigpy.zcl.clusters.measurement import CarbonDioxideConcentration

from zhaquirks.builder import QuirkBuilder
from zhaquirks.clusters import CustomCluster
from zhaquirks.xiaomi import LUMI


class CarbonDioxideConcentrationCluster(CustomCluster, CarbonDioxideConcentration):
    """Carbon Dioxide concentration cluster that fixes the scaling issue."""

    def _update_attribute(self, attrid, value):
        """Fix CO2 concentration scaling by dividing by 1e6."""
        if attrid == CarbonDioxideConcentration.AttributeDefs.measured_value.id:
            # The device reports values with 6 extra zeros, so divide by 1e6
            value = value / 1_000_000
        super()._update_attribute(attrid, value)


(
    QuirkBuilder(LUMI, "lumi.airm.fhac01")
    .replaces(CarbonDioxideConcentrationCluster)
    .add_to_registry()
)
