"""Frient Electricity Meter Interface Norwegian HAN."""

from __future__ import annotations

from typing import Any

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
import zigpy.types as t
from zigpy.zcl.clusters.smartenergy import Metering


class FrientMetering(CustomCluster, Metering):
    """Frient EMI Norwegian HAN Metering cluster definition."""

    # fix device issue
    _CONSTANT_ATTRIBUTES = {Metering.AttributeDefs.divisor.id: 1000}

    def _update_attribute(self, attrid: int | t.uint16_t, value: Any) -> None:
        """Update attribute with value."""
        # prevent attribute_updated events for divisor
        if attrid == Metering.AttributeDefs.divisor.id:
            return
        super()._update_attribute(attrid, value)


(
    QuirkBuilder("frient A/S", "EMIZB-132")
    .replaces(FrientMetering, endpoint_id=2)
    .add_to_registry()
)
