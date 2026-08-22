"""Tests for the Aqara Multi-State Sensor P100 (lumi.vibration.agl002)."""

from types import SimpleNamespace
from unittest import mock

import pytest
from zha.application import EntityPlatform, EntityType, Platform
from zha.quirks import DEVICE_REGISTRY
from zigpy.zcl import ClusterType
from zigpy.zcl.clusters.closures import DoorLock
from zigpy.zcl.clusters.general import AnalogInput, OnOff, PowerConfiguration

from tests.common import ClusterListener
from tests.test_xiaomi import create_aqara_attr_report
import zhaquirks
from zhaquirks.xiaomi import XIAOMI_AQARA_ATTRIBUTE_E1
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


def test_p100_entity_discovery(p100_device):
    """The quirk exposes the intended HA entities and suppresses the wrong defaults.

    Guards the advertised Home Assistant surface: correct platform/type/primary
    for the created entities, and removal of the spurious lock/switch/analog-input
    entities ZHA would otherwise create from the raw signature.
    """
    quirk = DEVICE_REGISTRY.match_entry(p100_device).zha_device_factory.quirk_definition
    by_suffix = {m.resolved_unique_id_suffix: m for m in quirk.entity_metadata}

    # Contact sensor is the primary entity and lives on the OnOff cluster.
    contact = by_suffix["on_off"]
    assert contact.entity_platform == EntityPlatform.BINARY_SENSOR
    assert contact.primary is True
    assert contact.cluster_id == OnOff.cluster_id
    assert contact.endpoint_id == 1

    # Writable configuration entities.
    config_suffixes = {
        "device_mode",
        "door_window_type",
        "sensitivity",
        "report_interval",
        "movement_detection",
        "vibration_detection",
        "fall_detection",
        "orientation_detection",
        "triple_tap_detection",
    }
    assert config_suffixes <= by_suffix.keys()
    assert all(by_suffix[s].entity_type == EntityType.CONFIG for s in config_suffixes)

    # Read-only diagnostic sensors.
    for suffix in ("orientation", "device_posture"):
        assert by_suffix[suffix].entity_platform == EntityPlatform.SENSOR
        assert by_suffix[suffix].entity_type == EntityType.DIAGNOSTIC

    # Default entities ZHA would create from the raw signature must be suppressed.
    disabled = {(m.cluster_id, m.endpoint_id) for m in quirk.disabled_default_entities}
    assert (DoorLock.cluster_id, 1) in disabled  # fake lock
    assert (OnOff.cluster_id, 1) in disabled  # spurious switch
    assert (AnalogInput.cluster_id, 1) in disabled
    assert (AnalogInput.cluster_id, 2) in disabled

    # The OnOff suppression is filtered so only the switch is dropped and our
    # contact binary sensor (same cluster) survives.
    onoff_rule = next(
        m
        for m in quirk.disabled_default_entities
        if m.cluster_id == OnOff.cluster_id and m.endpoint_id == 1
    )
    assert onoff_rule.function is not None


def test_p100_battery_from_heartbeat(p100_device):
    """Battery tags in the Aqara heartbeat (0x00F7) feed the power cluster.

    The P100 reports battery data in the periodic Aqara blob, using tag 23 for
    voltage in mV and tag 24 for percentage. This exercises the heartbeat parsing
    path observed on real hardware.
    """
    opple_cluster = p100_device.endpoints[1].opple_cluster
    power_cluster = p100_device.endpoints[1].power
    power_listener = ClusterListener(power_cluster)

    voltage_id = PowerConfiguration.AttributeDefs.battery_voltage.id
    percent_id = PowerConfiguration.AttributeDefs.battery_percentage_remaining.id

    # Values taken from a real P100 heartbeat: 2903 mV, 100 %.
    opple_cluster.update_attribute(
        XIAOMI_AQARA_ATTRIBUTE_E1,
        create_aqara_attr_report({12: 10, 13: 24, 23: 2903, 24: 100, 101: 3}),
    )

    # Voltage in mV is stored as deci-volts on the voltage attribute.
    assert (voltage_id, 29.0) in power_listener.attribute_updates
    # The 0-100 percentage is stored as 0-200 (ZCL half-percent) and, because
    # XiaomiPowerConfigurationPercent is used, is taken from tag 24 rather than
    # being derived from the voltage.
    assert (percent_id, 200) in power_listener.attribute_updates


def test_p100_default_switch_filter():
    """The OnOff prevent-default filter removes the switch but not the contact sensor."""
    # entity.PLATFORM is ZHA's Platform enum.
    assert _is_default_switch(SimpleNamespace(PLATFORM=Platform.SWITCH)) is True
    assert _is_default_switch(SimpleNamespace(PLATFORM=Platform.BINARY_SENSOR)) is False
