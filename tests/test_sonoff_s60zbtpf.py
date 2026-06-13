"""Tests for the SONOFF S60ZBTPF device."""

import pytest
import zigpy.types as t
from zigpy.zcl import ClusterType, foundation
from zigpy.zcl.clusters.general import OnOff
from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement

import zhaquirks
from zhaquirks.sonoff.s60zbtpf import (
    S60_POWER_FIX_FW_VERSION,
    SonoffS60ElectricalMeasurement,
    SonoffS60OnOff,
)

zhaquirks.setup()

POWER_ID = ElectricalMeasurement.AttributeDefs.active_power.id
CURRENT_ID = ElectricalMeasurement.AttributeDefs.rms_current.id
VOLTAGE_ID = ElectricalMeasurement.AttributeDefs.rms_voltage.id
ON_OFF_ID = OnOff.AttributeDefs.on_off.id

# OnOff and ElectricalMeasurement are needed as stock clusters for the post-v2.0.3
# quirk, which (unlike the pre-v2.0.3 quirk) does not replace them.
S60_CLUSTERS = {
    1: {
        OnOff.cluster_id: ClusterType.Server,
        ElectricalMeasurement.cluster_id: ClusterType.Server,
    }
}


@pytest.mark.parametrize(
    "fw_version",
    [
        None,  # device does not report a firmware version
        S60_POWER_FIX_FW_VERSION - 1,  # firmware before the power fix
        0x00002002,  # v2.0.2
    ],
)
def test_sonoff_plug_power_fix(zigpy_device_from_v2_quirk, fw_version):
    """Test Sonoff plug power measurement overrides on pre-v2.0.3 firmware."""
    device = zigpy_device_from_v2_quirk(
        "SONOFF", "S60ZBTPF", cluster_ids=S60_CLUSTERS, firmware_version=fw_version
    )

    electrical_cluster = device.endpoints[1].electrical_measurement
    on_off_cluster = device.endpoints[1].on_off

    # the workaround clusters are applied
    assert isinstance(on_off_cluster, SonoffS60OnOff)
    assert isinstance(electrical_cluster, SonoffS60ElectricalMeasurement)

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


@pytest.mark.parametrize(
    "fw_version",
    [
        S60_POWER_FIX_FW_VERSION,  # v2.0.3, the version that fixed the bug
        S60_POWER_FIX_FW_VERSION + 1,  # newer than the fix
    ],
)
def test_sonoff_plug_no_power_fix_on_new_firmware(
    zigpy_device_from_v2_quirk, fw_version
):
    """Test the power workaround is not applied on v2.0.3 and newer firmware."""
    device = zigpy_device_from_v2_quirk(
        "SONOFF", "S60ZBTPF", cluster_ids=S60_CLUSTERS, firmware_version=fw_version
    )

    electrical_cluster = device.endpoints[1].electrical_measurement
    on_off_cluster = device.endpoints[1].on_off

    # the workaround clusters are NOT applied, stock ZHA clusters are used
    assert not isinstance(on_off_cluster, SonoffS60OnOff)
    assert not isinstance(electrical_cluster, SonoffS60ElectricalMeasurement)

    electrical_cluster.update_attribute(POWER_ID, 300)
    electrical_cluster.update_attribute(CURRENT_ID, 13)
    electrical_cluster.update_attribute(VOLTAGE_ID, 263)

    # turning the socket off does not reset the power readings
    on_off_cluster.update_attribute(ON_OFF_ID, t.Bool.false)
    assert electrical_cluster.get(POWER_ID) == 300
    assert electrical_cluster.get(CURRENT_ID) == 13
    assert electrical_cluster.get(VOLTAGE_ID) == 263
