"""Tests for Sonoff ZBM5 quirks."""

from unittest import mock

import pytest
from zha.application import Platform
from zha.quirks import DEVICE_REGISTRY
from zigpy.zcl import foundation

from tests.zha_helpers import join_device_from_diagnostics, zha_gateway
import zhaquirks
from zhaquirks.const import COMMAND_DOUBLE, COMMAND_HOLD, COMMAND_SINGLE, COMMAND_TRIPLE
from zhaquirks.sonoff.snzb01m import SonoffButtonCluster
from zhaquirks.sonoff.zbm5 import (
    DetachRelaySwitch,
    SonoffCluster,
    SonoffDetachedRelayMask,
)

zhaquirks.setup()


async def test_sonoff_zbm5_detach_relay_switches():
    """Test the relay switches follow the detached relay mask."""
    async with zha_gateway() as gateway:
        device = await join_device_from_diagnostics(
            gateway, "sonoff-zbm5-3c-80-86-0x00001004.json", DEVICE_REGISTRY
        )

        for relay in (1, 2, 3):
            entity = device.get_platform_entity(
                Platform.SWITCH,
                unique_id=f"ab:cd:ef:12:89:f3:cd:e6-1-relay_{relay}_detached",
            )

            assert type(entity) is DetachRelaySwitch
            assert entity.is_on


async def test_sonoff_zbm5_attach_relay():
    """Test turning off a relay switch clears its bit in the mask."""
    async with zha_gateway() as gateway:
        device = await join_device_from_diagnostics(
            gateway, "sonoff-zbm5-3c-80-86-0x00001004.json", DEVICE_REGISTRY
        )
        entity = device.get_platform_entity(
            Platform.SWITCH, unique_id="ab:cd:ef:12:89:f3:cd:e6-1-relay_2_detached"
        )
        sonoff_cluster = device.device.endpoints[1].sonoff_cluster

        write_response = [
            [foundation.WriteAttributesStatusRecord(status=foundation.Status.SUCCESS)]
        ]
        with mock.patch.object(
            sonoff_cluster,
            "write_attributes_raw",
            mock.AsyncMock(return_value=write_response),
        ) as mock_write:
            await entity.async_turn_off()

        [written_attr] = mock_write.mock_calls[0].args[0]
        assert written_attr.attrid == SonoffCluster.AttributeDefs.detach_relay_mask.id
        assert written_attr.value.value == (
            SonoffDetachedRelayMask.Relay1 | SonoffDetachedRelayMask.Relay3
        )
        assert not entity.is_on


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
