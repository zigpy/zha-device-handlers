"""Module for Xiaomi Aqara quirks implementations."""
import math
from zigpy.zcl.clusters.measurement import IlluminanceMeasurement
from zhaquirks import CustomCluster


class IlluminanceMeasurementCluster(CustomCluster, IlluminanceMeasurement):
    """Multistate input cluster."""

    cluster_id = IlluminanceMeasurement.cluster_id

    def _update_attribute(self, attrid, value):
        if attrid == 0 and value > 0:
            value = 10000 * math.log10(value + 1)
        super()._update_attribute(attrid, value)
