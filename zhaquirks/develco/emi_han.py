"""Frient Electricity Meter Interface Norwegian HAN."""

from __future__ import annotations

from zigpy.zcl.clusters.smartenergy import Metering

from zhaquirks.builder import QuirkBuilder
from zhaquirks.clusters import CustomCluster


class FrientMetering(CustomCluster, Metering):
    """Frient EMI Norwegian HAN Metering cluster definition.

    The device also has a manufacturer-specific "interface mode" attribute with the
    divisor's ID (0x0302), reported with the manufacturer-specific bit set. Since
    zigpy 0.91, such reports no longer update the ZCL divisor, so they aren't
    filtered anymore.

    The divisor is still forced to 1000, the fixed value from the technical manual.
    Installs from before zigpy 0.91 can have the interface mode value (512) cached as
    the divisor, and it's unverified what the device answers to a plain divisor read.
    """

    _CONSTANT_ATTRIBUTES = {Metering.AttributeDefs.divisor.id: 1000}


(
    QuirkBuilder("frient A/S", "EMIZB-132")
    .replaces(FrientMetering, endpoint_id=2)
    .add_to_registry()
)
