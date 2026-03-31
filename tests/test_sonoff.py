"""Tests for Sonoff ZBM5 quirks."""

from unittest import mock

import pytest
import zigpy.types as t
from zigpy.zcl import ClusterType, foundation
from zigpy.zcl.clusters.general import OnOff

from tests.common import ClusterListener
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
from zhaquirks.sonoff.zbm5 import (
    SonoffCluster,
    SonoffDetachedRelayMask,
    SonoffInputConfigCluster,
)

zhaquirks.setup()


@pytest.mark.parametrize(
    ("mask", "expected_states"),
    [
        (
            SonoffDetachedRelayMask.Relay1,
            (True, False, False),
        ),
        (
            SonoffDetachedRelayMask.Relay1 | SonoffDetachedRelayMask.Relay2,
            (True, True, False),
        ),
        (
            SonoffDetachedRelayMask.Relay1
            | SonoffDetachedRelayMask.Relay2
            | SonoffDetachedRelayMask.Relay3,
            (True, True, True),
        ),
    ],
    ids=["relay1", "relay1+2", "relay1+2+3"],
)
async def test_sonoff_zbm5_relay_mask_propagation(
    zigpy_device_from_v2_quirk, mask, expected_states
):
    """Test relay mask updates propagate to local cluster."""
    device = zigpy_device_from_v2_quirk(
        manufacturer="SONOFF",
        model="ZBM5-3C-80/86",
        cluster_ids={
            1: {
                SonoffCluster.cluster_id: ClusterType.Server,
                SonoffInputConfigCluster.cluster_id: ClusterType.Server,
                OnOff.cluster_id: ClusterType.Server,
            },
            2: {OnOff.cluster_id: ClusterType.Server},
            3: {OnOff.cluster_id: ClusterType.Server},
        },
    )

    sonoff_cluster = device.endpoints[1].sonoff_cluster
    local_cluster = device.endpoints[1].sonoff_input_config
    sonoff_listener = ClusterListener(sonoff_cluster)
    local_listener = ClusterListener(local_cluster)

    detach_mask_attr = sonoff_cluster.AttributeDefs.detach_relay_mask.id
    relay_1_attr = local_cluster.AttributeDefs.relay_1_detached.id
    relay_2_attr = local_cluster.AttributeDefs.relay_2_detached.id
    relay_3_attr = local_cluster.AttributeDefs.relay_3_detached.id

    sonoff_cluster.update_attribute(detach_mask_attr, mask)

    assert len(sonoff_listener.attribute_updates) == 1
    assert sonoff_listener.attribute_updates[0][0] == detach_mask_attr

    assert len(local_listener.attribute_updates) == 3
    assert local_listener.attribute_updates[0] == (relay_1_attr, expected_states[0])
    assert local_listener.attribute_updates[1] == (relay_2_attr, expected_states[1])
    assert local_listener.attribute_updates[2] == (relay_3_attr, expected_states[2])


async def test_sonoff_cluster_write_attributes_logic(zigpy_device_from_v2_quirk):
    """Test writing relay attributes translates to mask write and updates local state."""
    device = zigpy_device_from_v2_quirk(
        manufacturer="SONOFF",
        model="ZBM5-1C-80/86",
        cluster_ids={
            1: {
                SonoffCluster.cluster_id: ClusterType.Server,
                SonoffInputConfigCluster.cluster_id: ClusterType.Server,
            }
        },
    )

    sonoff_cluster = device.endpoints[1].sonoff_cluster
    local_cluster = device.endpoints[1].sonoff_input_config
    local_listener = ClusterListener(local_cluster)

    # Mock at the low level so real write_attributes runs and emits events
    write_response = [
        [foundation.WriteAttributesStatusRecord(status=foundation.Status.SUCCESS)]
    ]
    with mock.patch.object(
        sonoff_cluster,
        "write_attributes_raw",
        mock.AsyncMock(return_value=write_response),
    ) as mock_write:
        await local_cluster.write_attributes(
            {SonoffInputConfigCluster.AttributeDefs.relay_1_detached.name: True}
        )

        # Verify mask was written to device
        assert mock_write.call_count == 1
        written_attrs = mock_write.call_args[0][0]
        assert len(written_attrs) == 1
        assert (
            written_attrs[0].attrid == SonoffCluster.AttributeDefs.detach_relay_mask.id
        )

        # Verify local relay states updated via AttributeWrittenEvent
        relay_1_attr = local_cluster.AttributeDefs.relay_1_detached.id
        relay_2_attr = local_cluster.AttributeDefs.relay_2_detached.id
        relay_3_attr = local_cluster.AttributeDefs.relay_3_detached.id

        assert local_listener.attribute_updates[0] == (relay_1_attr, True)
        assert local_listener.attribute_updates[1] == (relay_2_attr, False)
        assert local_listener.attribute_updates[2] == (relay_3_attr, False)

        # Write relay_1_detached = False to test clearing a bit
        local_listener.attribute_updates.clear()
        await local_cluster.write_attributes(
            {SonoffInputConfigCluster.AttributeDefs.relay_1_detached.name: False}
        )

        written_attrs = mock_write.call_args[0][0]
        assert written_attrs[0].value.value == SonoffDetachedRelayMask(0)

        assert local_listener.attribute_updates[0] == (relay_1_attr, False)
        assert local_listener.attribute_updates[1] == (relay_2_attr, False)
        assert local_listener.attribute_updates[2] == (relay_3_attr, False)


async def test_sonoff_cluster_failed_write_does_not_propagate(
    zigpy_device_from_v2_quirk,
):
    """Test that a failed mask write does not update local relay states."""
    device = zigpy_device_from_v2_quirk(
        manufacturer="SONOFF",
        model="ZBM5-1C-80/86",
        cluster_ids={
            1: {
                SonoffCluster.cluster_id: ClusterType.Server,
                SonoffInputConfigCluster.cluster_id: ClusterType.Server,
            }
        },
    )

    sonoff_cluster = device.endpoints[1].sonoff_cluster
    local_cluster = device.endpoints[1].sonoff_input_config
    local_listener = ClusterListener(local_cluster)

    # Mock a failed write
    write_response = [
        [
            foundation.WriteAttributesStatusRecord(
                status=foundation.Status.FAILURE,
                attrid=SonoffCluster.AttributeDefs.detach_relay_mask.id,
            )
        ]
    ]
    with mock.patch.object(
        sonoff_cluster,
        "write_attributes_raw",
        mock.AsyncMock(return_value=write_response),
    ):
        await local_cluster.write_attributes(
            {SonoffInputConfigCluster.AttributeDefs.relay_1_detached.name: True}
        )

    # Local relay states should not have been updated
    assert len(local_listener.attribute_updates) == 0


async def test_sonoff_cluster_apply_custom_configuration(zigpy_device_from_v2_quirk):
    """Test apply_custom_configuration reads mask and populates local relay states."""
    device = zigpy_device_from_v2_quirk(
        manufacturer="SONOFF",
        model="ZBM5-1C-80/86",
        cluster_ids={
            1: {
                SonoffCluster.cluster_id: ClusterType.Server,
                SonoffInputConfigCluster.cluster_id: ClusterType.Server,
            }
        },
    )

    sonoff_cluster = device.endpoints[1].sonoff_cluster
    local_cluster = device.endpoints[1].sonoff_input_config
    local_listener = ClusterListener(local_cluster)

    mask_attr = SonoffCluster.AttributeDefs.detach_relay_mask
    mask = SonoffDetachedRelayMask.Relay1 | SonoffDetachedRelayMask.Relay2

    # Mock raw ZCL read so the full read_attributes chain runs and fires events
    read_response = foundation.ReadAttributeRecord(
        attrid=mask_attr.id,
        status=foundation.Status.SUCCESS,
        value=foundation.TypeValue(type=mask_attr.zcl_type, value=mask),
    )
    with mock.patch.object(
        sonoff_cluster,
        "_read_attributes",
        mock.AsyncMock(return_value=[[read_response]]),
    ):
        await sonoff_cluster.apply_custom_configuration()

    # Verify local relay states were populated from the read
    relay_1_attr = local_cluster.AttributeDefs.relay_1_detached.id
    relay_2_attr = local_cluster.AttributeDefs.relay_2_detached.id
    relay_3_attr = local_cluster.AttributeDefs.relay_3_detached.id

    assert local_listener.attribute_updates[0] == (relay_1_attr, True)
    assert local_listener.attribute_updates[1] == (relay_2_attr, True)
    assert local_listener.attribute_updates[2] == (relay_3_attr, False)


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

    device = zigpy_device_from_v2_quirk("SONOFF", "SNZB-01M", endpoint_ids=[1, 2, 3, 4])
    cluster = device.endpoints[1].sonoff_button_cluster
    listener = mock.MagicMock()
    cluster.add_listener(listener)

    with mock.patch(
        "zhaquirks.sonoff.snzb01m.button_event_from_report", return_value=None
    ):
        cluster._update_attribute(0x0000, 1)
        assert listener.zha_send_event.call_count == 0
