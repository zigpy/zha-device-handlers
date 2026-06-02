"""Module for Innr quirks implementations."""

import logging

from zigpy.quirks import CustomCluster
from zigpy.zcl import ReportingConfig, foundation
from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement
from zigpy.zcl.clusters.smartenergy import Metering

_LOGGER = logging.getLogger(__name__)

INNR = "innr"


class LimitedReportingClusterMixin(CustomCluster):
    """Only configure attribute reporting for an explicit allow-list.

    Some Innr plugs (e.g. the SP 120, see zigpy/zha-device-handlers#4652) run
    firmware that *accepts* a Configure Reporting request for attributes they do
    not actually support, instead of rejecting it with ``UNSUPPORTED_ATTRIBUTE``.
    Every accepted-but-useless reporting configuration still occupies a slot in
    the device's small reporting table. Once that table is full, configuring
    reporting for an attribute that *is* supported -- notably the energy meter's
    ``current_summ_delivered`` -- silently fails, so that sensor only updates
    from the start-up read instead of being reported live.

    This restricts reporting setup to the handful of attributes the device
    really supports (``_REPORTING_ALLOWED``), so the reporting table cannot be
    flooded. Skipped attributes are acknowledged as successfully configured so
    the wrapping integration neither surfaces them as failures nor keeps
    retrying them.

    It subclasses ``CustomCluster`` (rather than being a bare mixin) only so
    ``super()`` and ``self`` resolve against the cluster API; it defines no
    ``cluster_id`` and must be combined before a concrete backing cluster in the
    MRO, e.g. ``class Foo(LimitedReportingClusterMixin, SomeInnrCluster)``.
    """

    # Attribute IDs this device supports configuring reporting for.
    _REPORTING_ALLOWED: frozenset[int] = frozenset()

    async def configure_reporting_multiple(
        self, config: dict[foundation.ZCLAttributeDef, ReportingConfig]
    ) -> dict[foundation.ZCLAttributeDef, foundation.Status]:
        """Forward only allow-listed attributes to the real request."""
        allowed = {a: c for a, c in config.items() if a.id in self._REPORTING_ALLOWED}
        skipped = [a for a in config if a.id not in self._REPORTING_ALLOWED]
        if skipped:
            _LOGGER.debug(
                "%s: skipping reporting setup for unsupported attributes: %s",
                self.ep_attribute,
                [a.name for a in skipped],
            )
        result = await super().configure_reporting_multiple(allowed) if allowed else {}
        for attr_def in skipped:
            result.setdefault(attr_def, foundation.Status.SUCCESS)
        return result

    async def configure_reporting(
        self,
        attribute: foundation.ZCLAttributeDef | int | str,
        min_interval: int,
        max_interval: int,
        reportable_change: int,
    ) -> dict[foundation.ZCLAttributeDef, foundation.Status]:
        """Forward a single attribute only when it is allow-listed."""
        attr_def = (
            attribute
            if isinstance(attribute, foundation.ZCLAttributeDef)
            else self.find_attribute(attribute)
        )
        if attr_def.id not in self._REPORTING_ALLOWED:
            _LOGGER.debug(
                "%s: skipping reporting setup for unsupported attribute: %s",
                self.ep_attribute,
                attr_def.name,
            )
            return {attr_def: foundation.Status.SUCCESS}
        return await super().configure_reporting(
            attribute, min_interval, max_interval, reportable_change
        )


class MeteringClusterInnrOld(CustomCluster, Metering):
    """Provide constant multiplier and divisor for old Innr plug firmware.

    Old firmware provides incorrect values for the divisor, so we override them.
    """

    _CONSTANT_ATTRIBUTES = {
        Metering.AttributeDefs.multiplier.id: 1,
        Metering.AttributeDefs.divisor.id: 100,
    }


class MeteringClusterInnrNew(CustomCluster, Metering):
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


class MeteringClusterInnrSP120(LimitedReportingClusterMixin, MeteringClusterInnrOld):
    """SP 120 metering cluster that only reports the attributes it supports."""

    _REPORTING_ALLOWED = frozenset(
        {
            Metering.AttributeDefs.instantaneous_demand.id,
            Metering.AttributeDefs.current_summ_delivered.id,
            Metering.AttributeDefs.status.id,
        }
    )


class ElectricalMeasurementClusterInnrSP120(
    LimitedReportingClusterMixin, ElectricalMeasurementClusterInnr
):
    """SP 120 electrical measurement cluster limited to supported attributes."""

    _REPORTING_ALLOWED = frozenset(
        {
            ElectricalMeasurement.AttributeDefs.active_power.id,
            ElectricalMeasurement.AttributeDefs.rms_current.id,
            ElectricalMeasurement.AttributeDefs.rms_voltage.id,
        }
    )
