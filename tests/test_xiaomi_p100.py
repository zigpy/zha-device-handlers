"""Tests for the Aqara Multi-State Sensor P100 (lumi.vibration.agl002)."""

from types import SimpleNamespace
from unittest import mock

import pytest
from zha.application import Platform
from zigpy.zcl import ClusterType
from zigpy.zcl.clusters.closures import DoorLock
from zigpy.zcl.clusters.general import OnOff, PowerConfiguration

from tests.common import ClusterListener
import zhaquirks
from zhaquirks.xiaomi.aqara.multi_sensor_p100 import (
    ACTION_FALL,
    ACTION_MOVEMENT,
    ACTION_ORIENTATION,
    ACTION_STATIC,
    ACTION_TRIPLE_TAP,
    ACTION_VIBRATION,
    P100ActionCluster,
    P100ManufacturerCluster,
    _is_default_switch,
)

zhaquirks.setup()


@pytest.fixture
def p100_device(zigpy_device_from_v2_quirk):
    """Create a P100 device with the manufacturer and action clusters present."""
    return zigpy_device_from_v2_quirk(
        "Aqara",
        "lumi.vibration.agl002",
        cluster_ids={
            1: {
                DoorLock.cluster_id: ClusterType.Server,
                OnOff.cluster_id: ClusterType.Server,
            }
        },
    )


@pytest.mark.parametrize(
    ("value", "expected_action"),
    [
        (0, ACTION_TRIPLE_TAP),
        (1, ACTION_MOVEMENT),
        (2, ACTION_VIBRATION),
        (3, ACTION_ORIENTATION),
        (4, ACTION_FALL),
    ],
)
def test_p100_action_events(p100_device, value, expected_action):
    """The DoorLock 0x0055 attribute is translated into action zha_events."""
    action_cluster = p100_device.endpoints[1].door_lock
    assert isinstance(action_cluster, P100ActionCluster)

    zha_listener = mock.MagicMock()
    action_cluster.add_listener(zha_listener)

    action_cluster.update_attribute(0x0055, value)

    assert zha_listener.zha_send_event.mock_calls == [mock.call(expected_action, {})]


def test_p100_unknown_action_is_ignored(p100_device):
    """Unknown action codes do not emit an event."""
    action_cluster = p100_device.endpoints[1].door_lock
    zha_listener = mock.MagicMock()
    action_cluster.add_listener(zha_listener)

    action_cluster.update_attribute(0x0055, 99)

    assert zha_listener.zha_send_event.mock_calls == []


def test_p100_static_event(p100_device):
    """The manufacturer cluster 0x01F3 flag emits a 'static' action."""
    opple_cluster = p100_device.endpoints[1].opple_cluster
    assert isinstance(opple_cluster, P100ManufacturerCluster)

    zha_listener = mock.MagicMock()
    opple_cluster.add_listener(zha_listener)

    opple_cluster.update_attribute(P100ManufacturerCluster.STATIC_STATE_ATTR_ID, 1)
    assert zha_listener.zha_send_event.mock_calls == [mock.call(ACTION_STATIC, {})]

    # A 0 value should not emit anything.
    zha_listener.reset_mock()
    opple_cluster.update_attribute(P100ManufacturerCluster.STATIC_STATE_ATTR_ID, 0)
    assert zha_listener.zha_send_event.mock_calls == []


def test_p100_entities_created(p100_device):
    """The custom clusters are applied to the quirked device."""
    assert isinstance(p100_device.endpoints[1].opple_cluster, P100ManufacturerCluster)
    assert isinstance(p100_device.endpoints[1].door_lock, P100ActionCluster)
    # XiaomiPowerConfigurationPercent is added for battery reporting.
    assert p100_device.endpoints[1].power is not None


def test_p100_battery_direct_attributes(p100_device):
    """Direct battery attributes (0x17/0x18) feed the power cluster."""
    opple_cluster = p100_device.endpoints[1].opple_cluster
    power_cluster = p100_device.endpoints[1].power
    power_listener = ClusterListener(power_cluster)

    voltage_id = PowerConfiguration.AttributeDefs.battery_voltage.id
    percent_id = PowerConfiguration.AttributeDefs.battery_percentage_remaining.id

    # 0x18: 0-100 percentage -> stored as 0-200 (ZCL half-percent).
    opple_cluster.update_attribute(
        P100ManufacturerCluster.AttributeDefs.battery_percentage.id, 80
    )
    assert (percent_id, 160) in power_listener.attribute_updates

    # 0x17: voltage in mV -> stored as deci-volts on the voltage attribute.
    opple_cluster.update_attribute(
        P100ManufacturerCluster.AttributeDefs.battery_voltage.id, 3000
    )
    assert (voltage_id, 30) in power_listener.attribute_updates


def test_p100_default_switch_filter():
    """The OnOff prevent-default filter removes the switch but not the contact sensor."""
    # entity.PLATFORM is ZHA's Platform enum.
    assert _is_default_switch(SimpleNamespace(PLATFORM=Platform.SWITCH)) is True
    assert _is_default_switch(SimpleNamespace(PLATFORM=Platform.BINARY_SENSOR)) is False
