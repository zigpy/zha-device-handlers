"""Tests for the BITUO TECHNIK SPM01X energy meter."""  # codespell:ignore technik

from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement

import zhaquirks

zhaquirks.setup()

PHANTOM_PHASE_BC_ATTRS = (
    ElectricalMeasurement.AttributeDefs.active_power_ph_b.id,
    ElectricalMeasurement.AttributeDefs.active_power_ph_c.id,
    ElectricalMeasurement.AttributeDefs.rms_current_ph_b.id,
    ElectricalMeasurement.AttributeDefs.rms_current_ph_c.id,
    ElectricalMeasurement.AttributeDefs.rms_voltage_ph_b.id,
    ElectricalMeasurement.AttributeDefs.rms_voltage_ph_c.id,
    ElectricalMeasurement.AttributeDefs.power_factor_ph_b.id,
    ElectricalMeasurement.AttributeDefs.power_factor_ph_c.id,
)


async def test_spm01x_phantom_reports_swallowed(zigpy_device_from_v2_quirk):
    """Phantom Phase B/C reports are ignored and never cached.

    The firmware reports these attributes even though the device is single phase.
    """
    manufacturer = "BITUO TECHNIK"  # codespell:ignore technik
    device = zigpy_device_from_v2_quirk(manufacturer, "SPM01X")
    electrical_cluster = device.endpoints[1].electrical_measurement

    for attr_id in PHANTOM_PHASE_BC_ATTRS:
        # Simulate a device report (0xFFFF placeholder).
        electrical_cluster.update_attribute(attr_id, 0xFFFF)
        # The value is swallowed: nothing cached.
        assert electrical_cluster.get(attr_id) is None

    # Phase A attributes are still cached normally.
    electrical_cluster.update_attribute(
        ElectricalMeasurement.AttributeDefs.active_power.id, 100
    )
    assert (
        electrical_cluster.get(ElectricalMeasurement.AttributeDefs.active_power.id)
        == 100
    )
