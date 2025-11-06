"""Cleaned tests for Sonoff quirks (v2)."""

from unittest import mock

import pytest
import zigpy.types as t
from zigpy.zcl import foundation

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
    ACTION_MAP,
    SNZB01M,
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
    event = button_event_from_report(endpoint_id, value)

    assert event is not None
    assert event["endpoint_id"] == endpoint_id
    assert event["event"] == expected_action
    assert event["button"] == f"button{endpoint_id}"


def test_button_event_from_report_invalid_value():
    event = button_event_from_report(1, 99)
    assert event is None


async def test_snzb01m_button_events(zigpy_device_from_quirk):
    device = zigpy_device_from_quirk(SNZB01M)

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


async def test_snzb01m_invalid_attribute_update(zigpy_device_from_quirk):
    device = zigpy_device_from_quirk(SNZB01M)
    cluster = device.endpoints[1].sonoff_button_cluster
    listener = mock.MagicMock()
    cluster.add_listener(listener)

    cluster._update_attribute(0x0000, 99)
    assert listener.zha_send_event.call_count == 0


async def test_snzb01m_non_button_attribute_update(zigpy_device_from_quirk):
    device = zigpy_device_from_quirk(SNZB01M)
    cluster = device.endpoints[1].sonoff_button_cluster
    listener = mock.MagicMock()
    cluster.add_listener(listener)

    cluster._update_attribute(0x0001, 1)
    assert listener.zha_send_event.call_count == 0


def test_snzb01m_device_automation_triggers():
    triggers = SNZB01M.device_automation_triggers
    assert len(triggers) == 16

    expected_actions = [SHORT_PRESS, DOUBLE_PRESS, LONG_PRESS, TRIPLE_PRESS]

    for ep in range(1, 5):
        for action in expected_actions:
            trigger_key = (action, f"button{ep}")
            assert trigger_key in triggers

            trigger_value = triggers[trigger_key]
            assert trigger_value[COMMAND] == action
            assert trigger_value["endpoint_id"] == ep

    for trigger_key in triggers:
        action, button = trigger_key
        assert action in expected_actions
        assert button in [f"button{i}" for i in range(1, 5)]


def test_sonoff_button_cluster_attributes():
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
    assert ACTION_MAP[1] == SHORT_PRESS
    assert ACTION_MAP[2] == DOUBLE_PRESS
    assert ACTION_MAP[3] == LONG_PRESS
    assert ACTION_MAP[4] == TRIPLE_PRESS
    assert len(ACTION_MAP) == 4


def test_button_event_from_report_all_endpoints():
    for endpoint_id in [1, 2, 3, 4]:
        for value, expected_action in ACTION_MAP.items():
            event = button_event_from_report(endpoint_id, value)
            assert event is not None
            assert event["endpoint_id"] == endpoint_id
            assert event["event"] == expected_action
            assert event["button"] == f"button{endpoint_id}"


async def test_sonoff_button_cluster_listener_event(zigpy_device_from_quirk):
    device = zigpy_device_from_quirk(SNZB01M)
    cluster = device.endpoints[1].sonoff_button_cluster
    listener = mock.MagicMock()
    cluster.add_listener(listener)

    event_data = {"endpoint_id": 1, "event": SHORT_PRESS, "button": "button1"}
    cluster.listener_event(ZHA_SEND_EVENT, SHORT_PRESS, event_data)

    assert listener.zha_send_event.call_count == 1
    assert listener.zha_send_event.call_args[0][0] == SHORT_PRESS
    assert listener.zha_send_event.call_args[0][1] == event_data


async def test_sonoff_button_cluster_super_update_attribute(zigpy_device_from_quirk):
    device = zigpy_device_from_quirk(SNZB01M)
    cluster = device.endpoints[1].sonoff_button_cluster

    with mock.patch.object(cluster.__class__.__bases__[0], "_update_attribute") as mock_super:
        cluster._update_attribute(0x0000, 1)
        mock_super.assert_called_once_with(0x0000, 1)


def test_button_event_from_report_edge_cases():
    for endpoint_id in [0, 5, 10, 255]:
        event = button_event_from_report(endpoint_id, 1)
        assert event is not None
        assert event["endpoint_id"] == endpoint_id
        assert event["button"] == f"button{endpoint_id}"

    for invalid_value in [0, 5, -1, 256, None]:
        event = button_event_from_report(1, invalid_value)
        assert event is None


def test_snzb01m_cluster_constants():
    assert SONOFF_CLUSTER_ID_FC12 == 0xFC12
    assert SonoffButtonCluster.cluster_id == 0xFC12


async def test_sonoff_button_cluster_update_attribute_no_event(zigpy_device_from_quirk):
    device = zigpy_device_from_quirk(SNZB01M)
    cluster = device.endpoints[1].sonoff_button_cluster
    listener = mock.MagicMock()
    cluster.add_listener(listener)

    with mock.patch("zhaquirks.sonoff.snzb01m.button_event_from_report", return_value=None):
        cluster._update_attribute(0x0000, 1)
        assert listener.zha_send_event.call_count == 0
