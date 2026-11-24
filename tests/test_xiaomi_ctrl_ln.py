"""Tests for the Aqara wall switches with neutral in zhaquirks.xiaomi.aqara.ctrl_ln."""

import pytest
from zigpy.zcl.clusters.general import OnOff
from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement
from zigpy.zcl.clusters.smartenergy import Metering

from tests.common import ClusterListener
from tests.test_xiaomi import create_aqara_attr_report
import zhaquirks
from zhaquirks.legacy import get_device
from zhaquirks.xiaomi import XIAOMI_AQARA_ATTRIBUTE, OnOffCluster
from zhaquirks.xiaomi.aqara.ctrl_ln import CtrlLn, SwitchD1DoubleNeutral

zhaquirks.setup()


@pytest.mark.parametrize(
    "quirk, model",
    [
        (CtrlLn, "lumi.ctrl_ln1.aq1"),
        (CtrlLn, "lumi.ctrl_ln2.aq1"),
        (SwitchD1DoubleNeutral, "lumi.switch.b2nacn02"),
    ],
)
async def test_ctrl_ln_energy_from_heartbeat(zigpy_device_from_quirk, quirk, model):
    """Test energy, voltage and power in the 0xFF01 report reach the local clusters."""

    raw_device = zigpy_device_from_quirk(quirk, apply_quirk=False)
    raw_device.model = model
    device = quirk(raw_device.application, raw_device.ieee, raw_device.nwk, raw_device)
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


@pytest.mark.parametrize(
    "quirk, model",
    [
        (CtrlLn, "lumi.ctrl_ln1.aq1"),
        (CtrlLn, "lumi.ctrl_ln2.aq1"),
        (SwitchD1DoubleNeutral, "lumi.switch.b2nacn02"),
    ],
)
def test_ctrl_ln_quirk_match(zigpy_device_from_quirk, quirk, model):
    """Test each model gets its own quirk from the registry."""

    raw_device = zigpy_device_from_quirk(CtrlLn, apply_quirk=False)
    raw_device.model = model

    assert type(get_device(raw_device)) is quirk


def test_d1_double_neutral_standard_on_off(zigpy_device_from_quirk):
    """Test the D1 switch uses standard On/Off clusters and keeps configuration."""

    device = zigpy_device_from_quirk(SwitchD1DoubleNeutral)

    for endpoint_id in (1, 2):
        on_off = device.endpoints[endpoint_id].in_clusters[OnOff.cluster_id]
        assert type(on_off) is OnOff
    assert not device.skip_configuration

    # The ctrl_ln switches keep the raw On/Off frames and skip configuration
    ctrl_ln = zigpy_device_from_quirk(CtrlLn)
    assert isinstance(ctrl_ln.endpoints[1].in_clusters[OnOff.cluster_id], OnOffCluster)
    assert ctrl_ln.skip_configuration
