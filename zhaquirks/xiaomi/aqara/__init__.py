"""Module for Xiaomi Aqara quirks implementations."""
import math
from zigpy.zcl.clusters.measurement import (
    IlluminanceMeasurement, TemperatureMeasurement)
from zhaquirks import CustomCluster


class IlluminanceMeasurementCluster(CustomCluster, IlluminanceMeasurement):
    """Multistate input cluster."""

    cluster_id = IlluminanceMeasurement.cluster_id

    def _update_attribute(self, attrid, value):
        if attrid == 0 and value > 0:
            value = 10000 * math.log10(value) + 1
        super()._update_attribute(attrid, value)


class TemperatureMeasurementCluster(CustomCluster, TemperatureMeasurement):
    """Temperature cluster that filters out invalid temperature readings."""

    cluster_id = TemperatureMeasurement.cluster_id

    def _update_attribute(self, attrid, value):
        # drop values above and below documented range for this sensor
        # value is in centi degrees
        if attrid == 0 and (value >= -2000 or value <= 6000):
            super()._update_attribute(attrid, value)
