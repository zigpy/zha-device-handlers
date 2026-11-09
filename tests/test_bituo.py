"""Tests for the BITUO TECHNIK SPM01X energy meter."""  # codespell:ignore technik

from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement

import zhaquirks

zhaquirks.setup()

# The placeholder values the firmware actually reports for each phantom attribute.
PHANTOM_ATTR_VALUES = {
    ElectricalMeasurement.AttributeDefs.total_active_power.id: 0,
    ElectricalMeasurement.AttributeDefs.active_power_ph_b.id: -1,
    ElectricalMeasurement.AttributeDefs.active_power_ph_c.id: -1,
    ElectricalMeasurement.AttributeDefs.rms_current_ph_b.id: 0xFFFF,
    ElectricalMeasurement.AttributeDefs.rms_current_ph_c.id: 0xFFFF,
    ElectricalMeasurement.AttributeDefs.rms_voltage_ph_b.id: 0xFFFF,
    ElectricalMeasurement.AttributeDefs.rms_voltage_ph_c.id: 0xFFFF,
    ElectricalMeasurement.AttributeDefs.power_factor_ph_b.id: 0,
    ElectricalMeasurement.AttributeDefs.power_factor_ph_c.id: 0,
}


async def test_spm01x_phantom_attrs_unsupported(zigpy_device_from_v2_quirk):
    """Phantom attributes always report as unsupported.

    The firmware reports these attributes (with placeholder values) even though
    the device is single phase. They must stay unsupported so ZHA does not create
    the phantom entities, even after a value has been cached.
    """
    manufacturer = "BITUO TECHNIK"  # codespell:ignore technik
    device = zigpy_device_from_v2_quirk(manufacturer, "SPM01X")
    electrical_cluster = device.endpoints[1].electrical_measurement

    for attr_id, value in PHANTOM_ATTR_VALUES.items():
        assert electrical_cluster.is_attribute_unsupported(attr_id)
        # A device report caches a value but must not flip them to supported.
        electrical_cluster.update_attribute(attr_id, value)
        assert electrical_cluster.is_attribute_unsupported(attr_id)

    # Phase A / single-phase attributes remain supported.
    assert not electrical_cluster.is_attribute_unsupported(
        ElectricalMeasurement.AttributeDefs.active_power.id
    )
