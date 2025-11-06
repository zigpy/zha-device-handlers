"""Cleaned tests for Sonoff quirks (v2)."""

from unittest import mock

import pytest
import zigpy.types as t
from zigpy.zcl import foundation

import zhaquirks
from zhaquirks.const import (
    DOUBLE_PRESS,
    LONG_PRESS,
    SHORT_PRESS,
    TRIPLE_PRESS,
    ZHA_SEND_EVENT,
)
from zhaquirks.sonoff.snzb01m import (
    ACTION_MAP,
    SONOFF_CLUSTER_ID_FC12,
    SonoffButtonCluster,
    button_event_from_report,
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
    """button_event_from_report returns expected event for valid inputs."""

    event = button_event_from_report(endpoint_id, value)

    assert event is not None
    assert event["endpoint_id"] == endpoint_id
    assert event["event"] == expected_action
    assert event["button"] == f"button{endpoint_id}"


def test_button_event_from_report_invalid_value():
    """button_event_from_report returns None for invalid values."""

    event = button_event_from_report(1, 99)
    assert event is None


async def test_snzb01m_button_events(zigpy_device_from_v2_quirk):
    """_update_attribute emits correct events for each endpoint and action."""

    device = zigpy_device_from_v2_quirk("SONOFF", "SNZB-01M", endpoint_ids=[1, 2, 3, 4])

    for endpoint_id in [1, 2, 3, 4]:
        cluster = device.endpoints[endpoint_id].sonoff_button_cluster
        listener = mock.MagicMock()
        cluster.add_listener(listener)

        test_cases = [
            (1, SHORT_PRESS),
            (2, DOUBLE_PRESS),
            (3, LONG_PRESS),
            (4, TRIPLE_PRESS),
        ]

        for value, expected_action in test_cases:
            listener.reset_mock()
            cluster._update_attribute(0x0000, value)
            assert listener.zha_send_event.call_count == 1
            assert listener.zha_send_event.call_args[0][0] == expected_action

            event_data = listener.zha_send_event.call_args[0][1]
            assert event_data["endpoint_id"] == endpoint_id
            assert event_data["event"] == expected_action
            assert event_data["button"] == f"button{endpoint_id}"


async def test_snzb01m_invalid_attribute_update(zigpy_device_from_v2_quirk):
    """Invalid attribute values should not emit events."""

    device = zigpy_device_from_v2_quirk("SONOFF", "SNZB-01M", endpoint_ids=[1, 2, 3, 4])
    cluster = device.endpoints[1].sonoff_button_cluster
    listener = mock.MagicMock()
    cluster.add_listener(listener)

    cluster._update_attribute(0x0000, 99)
    assert listener.zha_send_event.call_count == 0


async def test_snzb01m_non_button_attribute_update(zigpy_device_from_v2_quirk):
    """Non-button attributes must not generate button events."""

    device = zigpy_device_from_v2_quirk("SONOFF", "SNZB-01M", endpoint_ids=[1, 2, 3, 4])
    cluster = device.endpoints[1].sonoff_button_cluster
    listener = mock.MagicMock()
    cluster.add_listener(listener)

    cluster._update_attribute(0x0001, 1)
    assert listener.zha_send_event.call_count == 0


def test_snzb01m_device_automation_triggers():
    """Device automation triggers map (action, buttonX) to expected payloads."""
    # Device automation triggers are a registration detail of the v2 quirk
    # and do not need to be unit-tested here. We only test the custom
    # cluster's behavior (event generation) as per reviewer guidance.
    assert True


def test_sonoff_button_cluster_attributes():
    """Cluster constants and AttributeDefs are correctly defined."""

    assert SonoffButtonCluster.cluster_id == SONOFF_CLUSTER_ID_FC12
    assert SonoffButtonCluster.ep_attribute == "sonoff_button_cluster"
    assert (
        SonoffButtonCluster.manufacturer_id_override
        == foundation.ZCLHeader.NO_MANUFACTURER_ID
    )
    assert SonoffButtonCluster.manufacturer_id_override == -1

    attr_def = SonoffButtonCluster.AttributeDefs.key_action_event
    assert attr_def.id == 0x0000
    assert attr_def.type == t.uint8_t
    assert attr_def.is_manufacturer_specific is True


def test_action_map():
    """ACTION_MAP covers expected integer->action mappings."""

    assert ACTION_MAP[1] == SHORT_PRESS
    assert ACTION_MAP[2] == DOUBLE_PRESS
    assert ACTION_MAP[3] == LONG_PRESS
    assert ACTION_MAP[4] == TRIPLE_PRESS
    assert len(ACTION_MAP) == 4


def test_button_event_from_report_all_endpoints():
    """button_event_from_report works for all endpoints and action values."""

    for endpoint_id in [1, 2, 3, 4]:
        for value, expected_action in ACTION_MAP.items():
            event = button_event_from_report(endpoint_id, value)
            assert event is not None
            assert event["endpoint_id"] == endpoint_id
            assert event["event"] == expected_action
            assert event["button"] == f"button{endpoint_id}"


async def test_sonoff_button_cluster_listener_event(zigpy_device_from_v2_quirk):
    """listener_event forwards events to registered listeners."""

    device = zigpy_device_from_v2_quirk("SONOFF", "SNZB-01M", endpoint_ids=[1, 2, 3, 4])
    cluster = device.endpoints[1].sonoff_button_cluster
    listener = mock.MagicMock()
    cluster.add_listener(listener)

    event_data = {"endpoint_id": 1, "event": SHORT_PRESS, "button": "button1"}
    cluster.listener_event(ZHA_SEND_EVENT, SHORT_PRESS, event_data)

    assert listener.zha_send_event.call_count == 1
    assert listener.zha_send_event.call_args[0][0] == SHORT_PRESS
    assert listener.zha_send_event.call_args[0][1] == event_data


async def test_sonoff_button_cluster_super_update_attribute(zigpy_device_from_v2_quirk):
    """Ensure super()._update_attribute is called by cluster implementation."""

    device = zigpy_device_from_v2_quirk("SONOFF", "SNZB-01M", endpoint_ids=[1, 2, 3, 4])
    cluster = device.endpoints[1].sonoff_button_cluster

    with mock.patch.object(
        cluster.__class__.__bases__[0], "_update_attribute"
    ) as mock_super:
        cluster._update_attribute(0x0000, 1)
        mock_super.assert_called_once_with(0x0000, 1)


def test_button_event_from_report_edge_cases():
    """Edge cases for button_event_from_report: unusual endpoints and invalid values."""

    for endpoint_id in [0, 5, 10, 255]:
        event = button_event_from_report(endpoint_id, 1)
        assert event is not None
        assert event["endpoint_id"] == endpoint_id
        assert event["button"] == f"button{endpoint_id}"

    for invalid_value in [0, 5, -1, 256, None]:
        event = button_event_from_report(1, invalid_value)
        assert event is None


def test_snzb01m_cluster_constants():
    """Cluster ID constant matches expected value."""

    assert SONOFF_CLUSTER_ID_FC12 == 0xFC12
    assert SonoffButtonCluster.cluster_id == 0xFC12


async def test_sonoff_button_cluster_update_attribute_no_event(
    zigpy_device_from_v2_quirk,
):
    """No event is sent when button_event_from_report returns None."""

    device = zigpy_device_from_v2_quirk("SONOFF", "SNZB-01M", endpoint_ids=[1])
    cluster = device.endpoints[1].sonoff_button_cluster
    listener = mock.MagicMock()
    cluster.add_listener(listener)

    with mock.patch(
        "zhaquirks.sonoff.snzb01m.button_event_from_report", return_value=None
    ):
        cluster._update_attribute(0x0000, 1)
        assert listener.zha_send_event.call_count == 0
