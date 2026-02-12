"""Frient Electricity Meter Interface Norwegian HAN."""

from __future__ import annotations

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl.clusters.smartenergy import Metering


class FrientMetering(CustomCluster, Metering):
    """Frient EMI Norwegian HAN Metering cluster definition."""


(
    QuirkBuilder("frient A/S", "EMIZB-132")
    .replaces(FrientMetering, endpoint_id=2)
    .add_to_registry()
)
