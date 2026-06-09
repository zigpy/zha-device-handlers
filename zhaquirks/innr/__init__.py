"""Module for Innr quirks implementations."""

from zigpy.quirks import CustomCluster
import zigpy.types as t
from zigpy.zcl import AttributeReportedEvent, AttributeUpdatedEvent
from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement
from zigpy.zcl.clusters.smartenergy import Metering
from zigpy.zcl.foundation import ZCLAttributeDef

INNR = "innr"
INNR_MANUFACTURER_CODE = 0x1166


class _InnrMeteringAttributeDefs(Metering.AttributeDefs):
    """Metering attributes plus the manufacturer-specific summation Innr reports."""

    # Innr SP plug firmware reports the standard current_summ_delivered (0x0000)
    # with the manufacturer-specific bit set (Innr code 0x1166). Define that
    # attribute so zigpy parses the report instead of dropping it as unknown.
    current_summ_delivered_mfg = ZCLAttributeDef(
        id=0x0000,
        type=t.uint48_t,
        is_manufacturer_specific=True,
        manufacturer_code=INNR_MANUFACTURER_CODE,
    )


class _InnrMeteringSummationMirror:
    """Mixin mirroring the manufacturer-framed summation onto the ZCL attribute.

    Since zigpy 0.91, reported attributes are resolved against the frame's
    manufacturer code, so the standard ``current_summ_delivered`` carried in
    Innr's manufacturer-specific report no longer matches the ZCL attribute and
    is dropped -- energy then only updates on the startup read. We instead define
    the manufacturer-specific attribute the device actually reports (above) and,
    on each of its updates, mirror the value onto the standard ZCL attribute that
    the energy sensor reads.
    """

    AttributeDefs = _InnrMeteringAttributeDefs

    def __init__(self, *args, **kwargs) -> None:
        """Listen for the manufacturer-specific summation reports."""
        super().__init__(*args, **kwargs)
        self.on_event(AttributeReportedEvent.event_type, self._mirror_summation)
        self.on_event(AttributeUpdatedEvent.event_type, self._mirror_summation)

    def _mirror_summation(
        self, event: AttributeReportedEvent | AttributeUpdatedEvent
    ) -> None:
        """Mirror the manufacturer-specific summation onto the ZCL attribute."""
        if (
            event.attribute_name
            == _InnrMeteringAttributeDefs.current_summ_delivered_mfg.name
        ):
            self.update_attribute(
                Metering.AttributeDefs.current_summ_delivered, event.value
            )


class MeteringClusterInnrOld(_InnrMeteringSummationMirror, CustomCluster, Metering):
    """Provide constant multiplier and divisor for old Innr plug firmware.

    Old firmware provides incorrect values for the divisor, so we override them.
    """

    _CONSTANT_ATTRIBUTES = {
        Metering.AttributeDefs.multiplier.id: 1,
        Metering.AttributeDefs.divisor.id: 100,
    }


class MeteringClusterInnrNew(_InnrMeteringSummationMirror, CustomCluster, Metering):
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
