"""Tests for the SONOFF S60ZBTPF device."""

import pytest
from zigpy.zcl import ClusterType
from zigpy.zcl.clusters.general import OnOff
from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement

import zhaquirks.sonoff.s60zbtpf

zhaquirks.setup()

POWER_ID = ElectricalMeasurement.AttributeDefs.active_power.id
CURRENT_ID = ElectricalMeasurement.AttributeDefs.rms_current.id
VOLTAGE_ID = ElectricalMeasurement.AttributeDefs.rms_voltage.id
ON_OFF_ID = OnOff.AttributeDefs.on_off.id


@pytest.fixture
def device(zigpy_device_from_v2_quirk):
    """Create a SONOFF S60ZBTPF zigpy device mock for testing."""
    cluster_ids = {1: {ElectricalMeasurement.cluster_id: ClusterType.Server}}
    return zigpy_device_from_v2_quirk("SONOFF", "S60ZBTPF", cluster_ids=cluster_ids)


async def test_power_fix(device):
    """Test power measurement overrides."""
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
    assert electrical_cluster.get(VOLTAGE_ID) is None

    electrical_cluster.update_attribute(POWER_ID, 300)
    electrical_cluster.update_attribute(CURRENT_ID, 13)
    electrical_cluster.update_attribute(VOLTAGE_ID, 263)
    assert electrical_cluster.get(POWER_ID) == 0
    assert electrical_cluster.get(CURRENT_ID) == 0
    assert electrical_cluster.get(VOLTAGE_ID) is None

    on_off_cluster.update_attribute(ON_OFF_ID, True)
    assert electrical_cluster.get(POWER_ID) == 0
    assert electrical_cluster.get(CURRENT_ID) == 0
    assert electrical_cluster.get(VOLTAGE_ID) is None

    electrical_cluster.update_attribute(POWER_ID, 300)
    electrical_cluster.update_attribute(CURRENT_ID, 13)
    electrical_cluster.update_attribute(VOLTAGE_ID, 263)
    assert electrical_cluster.get(POWER_ID) == 300
    assert electrical_cluster.get(CURRENT_ID) == 13
    assert electrical_cluster.get(VOLTAGE_ID) == 263
