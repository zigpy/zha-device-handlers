"""Osram Smart+ Plug device."""

from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement

from zhaquirks.osram import OSRAM

(
    QuirkBuilder(OSRAM, "Plug 01")
    .removes(ElectricalMeasurement.cluster_id, endpoint_id=3)
    .add_to_registry()
)
