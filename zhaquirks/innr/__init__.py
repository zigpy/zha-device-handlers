"""Module for Innr quirks implementations."""

from zigpy.quirks import CustomCluster
from zigpy.zcl import foundation
from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement
from zigpy.zcl.clusters.smartenergy import Metering

INNR = "innr"


class MeteringClusterInnr(CustomCluster, Metering):
    """Base Innr Metering cluster fixing manufacturer-framed attribute reports.

    Innr SP plug firmware sends its device-initiated metering report with the
    manufacturer-specific bit set (Innr manufacturer code 0x1166), even though
    the report carries the *standard* ``current_summ_delivered`` (0x0000)
    attribute (bundled with a genuine manufacturer-specific attribute, 0x0430).

    Since zigpy 0.91, reported attributes are resolved against the frame's
    manufacturer code, so a standard attribute carried in a manufacturer frame
    no longer matches and the report is dropped -- energy then only updates on
    the startup read. Stripping the manufacturer context from incoming attribute
    reports lets zigpy match the standard ZCL attribute again, restoring the
    device-initiated energy updates that worked before.
    """

    def handle_cluster_general_request(
        self,
        hdr: foundation.ZCLHeader,
        args: list,
        *,
        dst_addressing=None,
    ) -> None:
        """Strip the manufacturer bit from device-initiated attribute reports."""
        if (
            hdr.command_id == foundation.GeneralCommand.Report_Attributes
            and hdr.frame_control.is_manufacturer_specific
        ):
            hdr = hdr.replace(
                frame_control=hdr.frame_control.replace(is_manufacturer_specific=0),
                manufacturer=None,
            )
        super().handle_cluster_general_request(hdr, args, dst_addressing=dst_addressing)


class MeteringClusterInnrOld(MeteringClusterInnr):
    """Provide constant multiplier and divisor for old Innr plug firmware.

    Old firmware provides incorrect values for the divisor, so we override them.
    """

    _CONSTANT_ATTRIBUTES = {
        Metering.AttributeDefs.multiplier.id: 1,
        Metering.AttributeDefs.divisor.id: 100,
    }


class MeteringClusterInnrNew(MeteringClusterInnr):
    """Provide constant multiplier and divisor for new Innr plug firmware.

    New firmware provides already provides correct value, but the old quirk will have
    persisted the static values in the database, so we need to force the new values
    to avoid users having to re-pair the device.
    """

    _CONSTANT_ATTRIBUTES = {
        Metering.AttributeDefs.multiplier.id: 1,
        Metering.AttributeDefs.divisor.id: 1000,
    }


class ElectricalMeasurementClusterInnr(CustomCluster, ElectricalMeasurement):
    """Fix multiplier and divisor for AC current and power."""

    _CONSTANT_ATTRIBUTES = {
        ElectricalMeasurement.AttributeDefs.ac_current_multiplier.id: 1,
        ElectricalMeasurement.AttributeDefs.ac_current_divisor.id: 1000,
        ElectricalMeasurement.AttributeDefs.ac_power_divisor.id: 1,
        ElectricalMeasurement.AttributeDefs.ac_power_multiplier.id: 1,
    }
