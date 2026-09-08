"""Tests for Sonoff quirks."""

from unittest import mock

import pytest

import zhaquirks
from zhaquirks.const import COMMAND_DOUBLE, COMMAND_HOLD, COMMAND_SINGLE, COMMAND_TRIPLE
from zhaquirks.sonoff.snzb01m import SonoffButtonCluster

zhaquirks.setup()

# The ZBM5 "detach relay" switches toggle individual bits of the real
# `detach_relay_mask` bitmap via the builder's `mask=` read-modify-write, so the
# quirk is purely declarative and carries no custom code to test here. The
# masked-switch behavior is covered by ZHA's switch entity tests.


@pytest.mark.parametrize("endpoint_id", [1, 2, 3, 4])
@pytest.mark.parametrize(
    ("value", "expected_command"),
    [
        (1, COMMAND_SINGLE),
        (2, COMMAND_DOUBLE),
        (3, COMMAND_HOLD),
        (4, COMMAND_TRIPLE),
    ],
)
async def test_snzb01m_button_events(
    zigpy_device_from_v2_quirk, endpoint_id, value, expected_command
):
    """Correct events are emitted for each endpoint and action."""

    device = zigpy_device_from_v2_quirk("SONOFF", "SNZB-01M", endpoint_ids=[1, 2, 3, 4])
    cluster = device.endpoints[endpoint_id].sonoff_button_cluster
    listener = mock.MagicMock()
    cluster.add_listener(listener)

    cluster.update_attribute(
        SonoffButtonCluster.AttributeDefs.key_action_event.id, value
    )
    assert listener.zha_send_event.call_count == 1
    listener.zha_send_event.assert_called_with(expected_command, {})


async def test_snzb01m_invalid_attribute_update(zigpy_device_from_v2_quirk):
    """Invalid attribute values should not emit events."""

    device = zigpy_device_from_v2_quirk("SONOFF", "SNZB-01M", endpoint_ids=[1, 2, 3, 4])
    cluster = device.endpoints[1].sonoff_button_cluster
    listener = mock.MagicMock()
    cluster.add_listener(listener)

    cluster.update_attribute(SonoffButtonCluster.AttributeDefs.key_action_event.id, 99)
    assert listener.zha_send_event.call_count == 0


async def test_snzb01m_non_button_attribute_update(zigpy_device_from_v2_quirk):
    """Non-button attributes must not generate button events."""

    device = zigpy_device_from_v2_quirk("SONOFF", "SNZB-01M", endpoint_ids=[1, 2, 3, 4])
    cluster = device.endpoints[1].sonoff_button_cluster
    listener = mock.MagicMock()
    cluster.add_listener(listener)

    cluster.update_attribute(0x0001, 1)
    assert listener.zha_send_event.call_count == 0
