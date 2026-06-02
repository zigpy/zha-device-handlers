"""Tests for Innr quirks."""

from unittest import mock

from zigpy.zcl import Cluster, ReportingConfig, foundation
from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement
from zigpy.zcl.clusters.smartenergy import Metering

import zhaquirks
from zhaquirks.innr.innr_sp120_plug import SP120

zhaquirks.setup()

_REPORTING = ReportingConfig(min_interval=1, max_interval=300, reportable_change=1)


async def test_sp120_metering_limits_reporting(zigpy_device_from_quirk):
    """SP120 metering only configures reporting for supported attributes."""
    device = zigpy_device_from_quirk(SP120)
    metering = device.endpoints[1].smartenergy_metering

    requested = {
        Metering.AttributeDefs.instantaneous_demand: _REPORTING,
        Metering.AttributeDefs.current_summ_delivered: _REPORTING,
        Metering.AttributeDefs.status: _REPORTING,
        # Tiered summation attributes the SP 120 does not support.
        Metering.AttributeDefs.current_tier1_summ_delivered: _REPORTING,
        Metering.AttributeDefs.current_tier2_summ_delivered: _REPORTING,
    }

    with mock.patch.object(
        Cluster, "configure_reporting_multiple", mock.AsyncMock(return_value={})
    ) as forwarded:
        result = await metering.configure_reporting_multiple(requested)

    sent = {a.name for a in forwarded.call_args.args[0]}
    assert sent == {"instantaneous_demand", "current_summ_delivered", "status"}
    # Skipped attributes are reported back as successfully configured.
    assert result[Metering.AttributeDefs.current_tier1_summ_delivered] == (
        foundation.Status.SUCCESS
    )


async def test_sp120_electrical_measurement_limits_reporting(zigpy_device_from_quirk):
    """SP120 electrical measurement drops static/unsupported attribute reporting."""
    device = zigpy_device_from_quirk(SP120)
    em = device.endpoints[1].electrical_measurement

    requested = {
        ElectricalMeasurement.AttributeDefs.active_power: _REPORTING,
        ElectricalMeasurement.AttributeDefs.rms_current: _REPORTING,
        ElectricalMeasurement.AttributeDefs.rms_voltage: _REPORTING,
        # Static scaling attributes never need reporting.
        ElectricalMeasurement.AttributeDefs.ac_power_divisor: _REPORTING,
        ElectricalMeasurement.AttributeDefs.ac_power_multiplier: _REPORTING,
        # Attributes a single-phase plug does not expose.
        ElectricalMeasurement.AttributeDefs.ac_frequency: _REPORTING,
    }

    with mock.patch.object(
        Cluster, "configure_reporting_multiple", mock.AsyncMock(return_value={})
    ) as forwarded:
        await em.configure_reporting_multiple(requested)

    sent = {a.name for a in forwarded.call_args.args[0]}
    assert sent == {"active_power", "rms_current", "rms_voltage"}


async def test_sp120_single_attribute_reporting_filtered(zigpy_device_from_quirk):
    """The single-attribute path is filtered too, without hitting the device."""
    device = zigpy_device_from_quirk(SP120)
    em = device.endpoints[1].electrical_measurement

    with mock.patch.object(
        Cluster, "configure_reporting", mock.AsyncMock(return_value={})
    ) as forwarded:
        # Allowed: forwarded to the real request.
        await em.configure_reporting(
            ElectricalMeasurement.AttributeDefs.active_power.id, 1, 300, 1
        )
        assert forwarded.call_count == 1

        # Not allowed: acknowledged without a request being sent.
        result = await em.configure_reporting(
            ElectricalMeasurement.AttributeDefs.ac_power_divisor.id, 1, 300, 1
        )
        assert forwarded.call_count == 1
        assert (
            result[ElectricalMeasurement.AttributeDefs.ac_power_divisor]
            == foundation.Status.SUCCESS
        )
