"""Tests for Sonoff quirks."""

from unittest import mock

import pytest
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.foundation import ZCLHeader
from typing import Any, cast

import zhaquirks
from zhaquirks.const import (
    COMMAND,
    DOUBLE_PRESS,
    LONG_PRESS,
    SHORT_PRESS,
    TRIPLE_PRESS,
    ZHA_SEND_EVENT,
)
from zhaquirks.sonoff.snzb01m import (
    SNZB01M,
    SonoffButtonCluster,
    button_event_from_report,
    ACTION_MAP,
    SONOFF_CLUSTER_ID_FC12,
)

zhaquirks.setup()


@pytest.mark.parametrize("endpoint_id", [1, 2, 3, 4])
@pytest.mark.parametrize(
    "value, expected_action",
    [
        (1, SHORT_PRESS),
        (2, DOUBLE_PRESS),
        (3, LONG_PRESS),
        (4, TRIPLE_PRESS),
    ],
)
def test_button_event_from_report(endpoint_id, value, expected_action):
    """Test button_event_from_report function."""
    event = button_event_from_report(endpoint_id, value)

    assert event is not None
    assert event["endpoint_id"] == endpoint_id
    assert event["event"] == expected_action
    assert event["button"] == f"button{endpoint_id}"


def test_button_event_from_report_invalid_value():
    """Test button_event_from_report with invalid value."""
    event = button_event_from_report(1, 99)
    assert event is None


async def test_snzb01m_button_events(zigpy_device_from_quirk):
    """Test SNZB01M button cluster events."""
    device = zigpy_device_from_quirk(SNZB01M)

    # Test each endpoint
    for endpoint_id in [1, 2, 3, 4]:
        cluster = device.endpoints[endpoint_id].sonoff_button_cluster
        listener = mock.MagicMock()
        cluster.add_listener(listener)

        # Test each button action
        test_cases = [
            (1, SHORT_PRESS),
            (2, DOUBLE_PRESS),
            (3, LONG_PRESS),
            (4, TRIPLE_PRESS),
        ]

        for value, expected_action in test_cases:
            listener.reset_mock()

            # Simulate attribute update
            cluster._update_attribute(0x0000, value)

            # Verify event was sent
            assert listener.zha_send_event.call_count == 1
            assert listener.zha_send_event.call_args[0][0] == expected_action

            event_data = listener.zha_send_event.call_args[0][1]
            assert event_data["endpoint_id"] == endpoint_id
            assert event_data["event"] == expected_action
            assert event_data["button"] == f"button{endpoint_id}"


async def test_snzb01m_invalid_attribute_update(zigpy_device_from_quirk):
    """Test SNZB01M cluster with invalid attribute value."""
    device = zigpy_device_from_quirk(SNZB01M)

    cluster = device.endpoints[1].sonoff_button_cluster
    listener = mock.MagicMock()
    cluster.add_listener(listener)

    # Test invalid action value
    cluster._update_attribute(0x0000, 99)

    # No event should be sent for invalid value
    assert listener.zha_send_event.call_count == 0


async def test_snzb01m_non_button_attribute_update(zigpy_device_from_quirk):
    """Test SNZB01M cluster with non-button attribute update."""
    device = zigpy_device_from_quirk(SNZB01M)

    cluster = device.endpoints[1].sonoff_button_cluster
    listener = mock.MagicMock()
    cluster.add_listener(listener)

    # Test non-button attribute
    cluster._update_attribute(0x0001, 1)

    # No event should be sent for non-button attribute
    assert listener.zha_send_event.call_count == 0


def test_snzb01m_device_automation_triggers():
    """Test SNZB01M device automation triggers."""
    triggers = SNZB01M.device_automation_triggers

    # Should have 16 total triggers (4 buttons × 4 actions)
    assert len(triggers) == 16

    # Test specific trigger keys and values
    expected_actions = [SHORT_PRESS, DOUBLE_PRESS, LONG_PRESS, TRIPLE_PRESS]

    for ep in range(1, 5):
        for action in expected_actions:
            trigger_key = (action, f"button{ep}")
            assert trigger_key in triggers

            trigger_value = triggers[trigger_key]
            assert trigger_value[COMMAND] == action
            assert trigger_value["endpoint_id"] == ep

    # Test that no unexpected triggers exist
    for trigger_key in triggers:
        action, button = trigger_key
        assert action in expected_actions
        assert button in [f"button{i}" for i in range(1, 5)]


def test_snzb01m_signature():
    """Test SNZB01M device signature."""
    signature = SNZB01M.signature

    # Check models info
    assert ("SONOFF", "SNZB-01M") in signature["models_info"]

    # Check all endpoints exist
    for ep_id in [1, 2, 3, 4]:
        assert ep_id in signature["endpoints"]
        ep = signature["endpoints"][ep_id]
        ep_input_clusters = cast(list[Any], ep["input_clusters"])
        assert 0xFC12 in ep_input_clusters


def test_snzb01m_replacement():
    """Test SNZB01M device replacement configuration."""
    replacement = SNZB01M.replacement

    # Check all endpoints have the custom cluster
    for ep_id in [1, 2, 3, 4]:
        assert ep_id in replacement["endpoints"]
        ep = replacement["endpoints"][ep_id]
        # Should contain the SonoffButtonCluster class, not just the ID
        input_clusters = cast(list[Any], ep["input_clusters"])
        assert SonoffButtonCluster in input_clusters


def test_sonoff_button_cluster_attributes():
    """Test SonoffButtonCluster attributes and constants."""
    assert SonoffButtonCluster.cluster_id == SONOFF_CLUSTER_ID_FC12
    assert SonoffButtonCluster.ep_attribute == "sonoff_button_cluster"
    # NO_MANUFACTURER_ID is actually -1, not 0xFFFF
    assert (
        SonoffButtonCluster.manufacturer_id_override
        == foundation.ZCLHeader.NO_MANUFACTURER_ID
    )
    assert SonoffButtonCluster.manufacturer_id_override == -1

    # Test AttributeDefs
    attr_def = SonoffButtonCluster.AttributeDefs.key_action_event
    assert attr_def.id == 0x0000
    assert attr_def.type == t.uint8_t
    assert attr_def.is_manufacturer_specific is True


def test_action_map():
    """Test ACTION_MAP dictionary."""
    assert ACTION_MAP[1] == SHORT_PRESS
    assert ACTION_MAP[2] == DOUBLE_PRESS
    assert ACTION_MAP[3] == LONG_PRESS
    assert ACTION_MAP[4] == TRIPLE_PRESS

    # Test all keys are covered
    assert len(ACTION_MAP) == 4


def test_button_event_from_report_all_endpoints():
    """Test button_event_from_report with all endpoints and actions."""
    # Test all valid combinations
    for endpoint_id in [1, 2, 3, 4]:
        for value, expected_action in ACTION_MAP.items():
            event = button_event_from_report(endpoint_id, value)
            assert event is not None
            assert event["endpoint_id"] == endpoint_id
            assert event["event"] == expected_action
            assert event["button"] == f"button{endpoint_id}"


async def test_sonoff_button_cluster_listener_event(zigpy_device_from_quirk):
    """Test SonoffButtonCluster listener_event method."""
    device = zigpy_device_from_quirk(SNZB01M)
    cluster = device.endpoints[1].sonoff_button_cluster
    listener = mock.MagicMock()
    cluster.add_listener(listener)

    # Test direct listener_event call
    event_data = {"endpoint_id": 1, "event": SHORT_PRESS, "button": "button1"}
    cluster.listener_event(ZHA_SEND_EVENT, SHORT_PRESS, event_data)

    assert listener.zha_send_event.call_count == 1
    assert listener.zha_send_event.call_args[0][0] == SHORT_PRESS
    assert listener.zha_send_event.call_args[0][1] == event_data


async def test_sonoff_button_cluster_super_update_attribute(zigpy_device_from_quirk):
    """Test SonoffButtonCluster calls super()._update_attribute."""
    device = zigpy_device_from_quirk(SNZB01M)
    cluster = device.endpoints[1].sonoff_button_cluster

    with mock.patch.object(cluster.__class__.__bases__[0], "_update_attribute") as mock_super:
        cluster._update_attribute(0x0000, 1)
        # Verify super()._update_attribute was called
        mock_super.assert_called_once_with(0x0000, 1)


def test_button_event_from_report_edge_cases():
    """Test button_event_from_report with edge cases."""
    # Test with different endpoint IDs
    for endpoint_id in [0, 5, 10, 255]:
        event = button_event_from_report(endpoint_id, 1)
        assert event is not None
        assert event["endpoint_id"] == endpoint_id
        assert event["button"] == f"button{endpoint_id}"

    # Test with various invalid values
    for invalid_value in [0, 5, -1, 256, None]:
        event = button_event_from_report(1, invalid_value)
        assert event is None


def test_snzb01m_cluster_constants():
    """Test all cluster constants and IDs."""
    assert SONOFF_CLUSTER_ID_FC12 == 0xFC12

    # Test the cluster ID matches
    assert SonoffButtonCluster.cluster_id == 0xFC12

    # Test all endpoints have correct profile and device type in signature
    signature = SNZB01M.signature
    for ep_id in [1, 2, 3, 4]:
        ep = signature["endpoints"][ep_id]
        assert ep["profile_id"] == 0x0104
        assert ep["device_type"] == 0x0001


async def test_sonoff_button_cluster_update_attribute_no_event(zigpy_device_from_quirk):
    """Test _update_attribute when button_event_from_report returns None."""
    device = zigpy_device_from_quirk(SNZB01M)
    cluster = device.endpoints[1].sonoff_button_cluster
    listener = mock.MagicMock()
    cluster.add_listener(listener)

    # Mock button_event_from_report to return None
    with mock.patch("zhaquirks.sonoff.snzb01m.button_event_from_report", return_value=None):
        cluster._update_attribute(0x0000, 1)
        # No event should be sent when button_event_from_report returns None
        assert listener.zha_send_event.call_count == 0
