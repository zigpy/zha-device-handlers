"""Quirk for LUMI lumi.airm.fhac01 air quality monitor."""

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl.clusters.general import DeviceTemperature
from zigpy.zcl.clusters.measurement import CarbonDioxideConcentration

from zhaquirks.xiaomi import LUMI


class CarbonDioxideConcentrationCluster(CustomCluster, CarbonDioxideConcentration):
    """Carbon Dioxide concentration cluster that fixes the scaling issue."""

    def _update_attribute(self, attrid, value):
        """Fix CO2 concentration scaling by dividing by 1e6."""
        if attrid == CarbonDioxideConcentration.AttributeDefs.measured_value.id:
            # The device reports values with 6 extra zeros, so divide by 1e6
            value = value / 1_000_000
        super()._update_attribute(attrid, value)


class CustomDeviceTemperature(CustomCluster, DeviceTemperature):
    """Temperature measurement cluster that fixes the scaling issue."""

    def _update_attribute(self, attrid, value):
        """Fix temperature scaling by multiplying by 100."""
        if attrid == DeviceTemperature.AttributeDefs.current_temperature.id:
            # The device reports temperature divided by 100, so multiply by 100
            value = value * 100
        super()._update_attribute(attrid, value)


(
    QuirkBuilder(LUMI, "lumi.airm.fhac01")
    .replaces(CarbonDioxideConcentrationCluster)
    .replaces(CustomDeviceTemperature)
    .add_to_registry()
)
