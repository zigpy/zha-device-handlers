"""Tests for the SONOFF S60ZBTPF device."""

from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import OnOff
from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement

import zhaquirks.sonoff.s60zbtpf

zhaquirks.setup()

POWER_ID = ElectricalMeasurement.AttributeDefs.active_power.id
CURRENT_ID = ElectricalMeasurement.AttributeDefs.rms_current.id
VOLTAGE_ID = ElectricalMeasurement.AttributeDefs.rms_voltage.id
ON_OFF_ID = OnOff.AttributeDefs.on_off.id


async def test_sonoff_plug_power_fix(zigpy_device_from_v2_quirk):
    """Test Sonoff plug power measurement overrides."""
    device = zigpy_device_from_v2_quirk("SONOFF", "S60ZBTPF")

    electrical_cluster = device.endpoints[1].electrical_measurement
    on_off_cluster = device.endpoints[1].on_off

    electrical_cluster.update_attribute(POWER_ID, 300)
    electrical_cluster.update_attribute(CURRENT_ID, 13)
    electrical_cluster.update_attribute(VOLTAGE_ID, 263)
    assert electrical_cluster.get(POWER_ID) == 300
    assert electrical_cluster.get(CURRENT_ID) == 13
    assert electrical_cluster.get(VOLTAGE_ID) == 263

    on_off_cluster.update_attribute(ON_OFF_ID, False)
    assert electrical_cluster.get(POWER_ID) == 0
    assert electrical_cluster.get(CURRENT_ID) == 0
    assert electrical_cluster.get(VOLTAGE_ID) == foundation.DataType.uint16.non_value

    electrical_cluster.update_attribute(POWER_ID, 300)
    electrical_cluster.update_attribute(CURRENT_ID, 13)
    electrical_cluster.update_attribute(VOLTAGE_ID, 263)
    assert electrical_cluster.get(POWER_ID) == 0
    assert electrical_cluster.get(CURRENT_ID) == 0
    assert electrical_cluster.get(VOLTAGE_ID) == foundation.DataType.uint16.non_value

    on_off_cluster.update_attribute(ON_OFF_ID, True)
    assert electrical_cluster.get(POWER_ID) == 0
    assert electrical_cluster.get(CURRENT_ID) == 0
    assert electrical_cluster.get(VOLTAGE_ID) == foundation.DataType.uint16.non_value

    electrical_cluster.update_attribute(POWER_ID, 300)
    electrical_cluster.update_attribute(CURRENT_ID, 13)
    electrical_cluster.update_attribute(VOLTAGE_ID, 263)
    assert electrical_cluster.get(POWER_ID) == 300
    assert electrical_cluster.get(CURRENT_ID) == 13
    assert electrical_cluster.get(VOLTAGE_ID) == 263
