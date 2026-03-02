"""Frient Electricity Meter Interface Norwegian HAN."""

from __future__ import annotations

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.smartenergy import Metering


class FrientMetering(CustomCluster, Metering):
    """Frient EMI Norwegian HAN Metering cluster definition."""

    # fix device issue
    _CONSTANT_ATTRIBUTES = {Metering.AttributeDefs.divisor.id: 1000}

    def handle_cluster_general_request(
        self,
        hdr: foundation.ZCLHeader,
        args: list,
        *,
        dst_addressing: t.Addressing.Group
        | t.Addressing.IEEE
        | t.Addressing.NWK
        | None = None,
    ) -> None:
        """Filter out incorrect divisor attribute reports from device."""
        if hdr.command_id == foundation.GeneralCommand.Report_Attributes:
            # Filter out divisor attribute reports
            args.attribute_reports = [
                attr
                for attr in args.attribute_reports
                if attr.attrid != Metering.AttributeDefs.divisor.id
            ]

            # Don't process if no attributes remain
            if not args.attribute_reports:
                return

        super().handle_cluster_general_request(hdr, args, dst_addressing=dst_addressing)


(
    QuirkBuilder("frient A/S", "EMIZB-132")
    .replaces(FrientMetering, endpoint_id=2)
    .add_to_registry()
)
