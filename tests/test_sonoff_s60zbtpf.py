"""Tests for the SONOFF S60ZBTPF device."""

import pytest
import zigpy.device
import zigpy.quirks
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import Basic, OnOff, Ota
from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement
from zigpy.zdo.types import NodeDescriptor

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
CURRENT_FILE_VERSION_ID = Ota.AttributeDefs.current_file_version.id


def _make_s60_device(MockAppController, ieee, fw_version):
    """Create a quirked S60ZBTPF device reporting the given OTA firmware version.

    `fw_version` of None means the device does not report a firmware version.
    """
    raw_device = zigpy.device.Device(MockAppController, ieee, zigpy.types.NWK(0x1234))
    raw_device.manufacturer = "SONOFF"
    raw_device.model = "S60ZBTPF"
    raw_device.node_desc = NodeDescriptor(manufacturer_code=1234)

    ep = raw_device.add_endpoint(1)
    ep.add_input_cluster(Basic.cluster_id)
    ep.add_input_cluster(OnOff.cluster_id)
    ep.add_input_cluster(ElectricalMeasurement.cluster_id)
    ota = ep.add_output_cluster(Ota.cluster_id)
    if fw_version is not None:
        ota.update_attribute(CURRENT_FILE_VERSION_ID, fw_version)

    quirked = zigpy.quirks.get_device(raw_device)
    MockAppController.devices[ieee] = quirked
    return quirked


@pytest.mark.parametrize(
    "fw_version",
    [
        None,  # device does not report a firmware version
        S60_POWER_FIX_FW_VERSION - 1,  # firmware before the power fix
        0x00002002,  # v2.0.2
    ],
)
def test_sonoff_plug_power_fix(MockAppController, ieee_mock, fw_version):
    """Test Sonoff plug power measurement overrides on pre-v2.0.3 firmware."""
    device = _make_s60_device(MockAppController, ieee_mock, fw_version)

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
    MockAppController, ieee_mock, fw_version
):
    """Test the power workaround is not applied on v2.0.3 and newer firmware."""
    device = _make_s60_device(MockAppController, ieee_mock, fw_version)

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
