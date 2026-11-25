"""Tests for the Aqara wall switches with neutral (lumi.ctrl_ln1.aq1 / lumi.ctrl_ln2.aq1)."""

import pytest
from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement
from zigpy.zcl.clusters.smartenergy import Metering

from tests.common import ClusterListener
from tests.test_xiaomi import create_aqara_attr_report
import zhaquirks
from zhaquirks.xiaomi import XIAOMI_AQARA_ATTRIBUTE
from zhaquirks.xiaomi.aqara.ctrl_ln import CtrlLn

zhaquirks.setup()


@pytest.mark.parametrize("model", ["lumi.ctrl_ln1.aq1", "lumi.ctrl_ln2.aq1"])
async def test_ctrl_ln_energy_from_heartbeat(zigpy_device_from_quirk, model):
    """Test energy, voltage and power in the 0xFF01 report reach the local clusters."""

    raw_device = zigpy_device_from_quirk(CtrlLn, apply_quirk=False)
    raw_device.model = model
    device = CtrlLn(raw_device.application, raw_device.ieee, raw_device.nwk, raw_device)
    assert device.model == model

    basic_cluster = device.endpoints[1].basic
    em_listener = ClusterListener(device.endpoints[1].electrical_measurement)
    se_listener = ClusterListener(device.endpoints[1].smartenergy_metering)

    basic_cluster.update_attribute(
        XIAOMI_AQARA_ATTRIBUTE,
        create_aqara_attr_report({149: 232.75, 150: 2300, 152: 45.5}),
    )

    assert se_listener.attribute_updates == [
        (Metering.AttributeDefs.current_summ_delivered.id, 232750)
    ]
    assert (
        ElectricalMeasurement.AttributeDefs.rms_voltage.id,
        230,
    ) in em_listener.attribute_updates
    assert (
        ElectricalMeasurement.AttributeDefs.active_power.id,
        455,
    ) in em_listener.attribute_updates
