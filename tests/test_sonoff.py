"""Tests for Sonoff ZBM5 quirks."""

import itertools
from unittest import mock

import pytest
from zigpy.profiles import zha
import zigpy.types as t
from zigpy.zcl import ClusterType, foundation
from zigpy.zcl.clusters.general import OnOff

from tests.common import ButtonEventRecorder, ClusterListener, send_command
import zhaquirks
from zhaquirks.const import COMMAND_DOUBLE, COMMAND_HOLD, COMMAND_SINGLE, COMMAND_TRIPLE
from zhaquirks.sonoff.snzb01m import SonoffButtonCluster
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


_TSNS = itertools.cycle(range(256))


def report_attribute(device, endpoint_id, cluster_id, attribute, value) -> None:
    """Receive an attribute report frame from one of the device's server clusters."""
    header = foundation.ZCLHeader.general(
        tsn=next(_TSNS),
        command_id=foundation.GeneralCommand.Report_Attributes,
        direction=foundation.Direction.Server_to_Client,
    )
    report = foundation.Attribute(
        attrid=attribute.id,
        value=foundation.TypeValue(
            type=attribute.zcl_type, value=attribute.type(value)
        ),
    )
    schema = foundation.GENERAL_COMMANDS[
        foundation.GeneralCommand.Report_Attributes
    ].schema
    device.packet_received(
        t.ZigbeePacket(
            src_ep=endpoint_id,
            dst_ep=1,
            tsn=header.tsn,
            profile_id=zha.PROFILE_ID,
            cluster_id=cluster_id,
            data=t.SerializableBytes(header.serialize() + schema([report]).serialize()),
        )
    )


def with_profile(device, device_type=zha.DeviceType.REMOTE_CONTROL):
    """Give the device's endpoints the ZHA profile, which ZHA's discovery needs."""
    for endpoint_id, endpoint in device.endpoints.items():
        if endpoint_id:
            endpoint.profile_id = zha.PROFILE_ID
            endpoint.device_type = device_type
    return device


ZBM5_CLUSTERS = {
    1: {
        SonoffCluster.cluster_id: ClusterType.Server,
        OnOff.cluster_id: ClusterType.Server,
    },
    2: {OnOff.cluster_id: ClusterType.Server},
    3: {OnOff.cluster_id: ClusterType.Server},
}


@pytest.mark.parametrize(
    ("model", "buttons"),
    [
        ("ZBM5-1C-80/86", {"button": 1}),
        ("ZBM5-1C-120", {"button": 1}),
        ("ZBM5-2C-80/86", {"button_1": 1, "button_2": 2}),
        ("ZBM5-2C-120", {"button_1": 1, "button_2": 2}),
        ("ZBM5-3C-80/86", {"button_1": 1, "button_2": 2, "button_3": 3}),
        ("ZBM5-3C-120", {"button_1": 1, "button_2": 2, "button_3": 3}),
    ],
)
async def test_zbm5_button_events(zigpy_device_from_v2_quirk, model, buttons):
    """Test the button event entities of the ZBM5 wall switches."""
    gangs = len(buttons)
    device = zigpy_device_from_v2_quirk(
        "SONOFF",
        model,
        cluster_ids={ep: ZBM5_CLUSTERS[ep] for ep in range(1, gangs + 1)},
    )
    with_profile(device, zha.DeviceType.ON_OFF_LIGHT_SWITCH)
    recorder = await ButtonEventRecorder.create(device)

    assert recorder.event_types() == dict.fromkeys(buttons, ["single_press"])

    for endpoint_id in buttons.values():
        send_command(device, endpoint_id, OnOff.cluster_id, "toggle")
        # Not a button press
        send_command(device, endpoint_id, OnOff.cluster_id, "on")

    assert recorder.pop() == [(button, "single_press") for button in buttons]


@pytest.mark.parametrize("model", ["WB01", "SNZB-01P", "CK-TLSR8656-SS5-01(7000)"])
async def test_ewelink_button_events(zigpy_device_from_v2_quirk, model):
    """Test the button event entity of the eWeLink/SONOFF wireless buttons."""
    device = zigpy_device_from_v2_quirk(
        "eWeLink", model, cluster_ids={1: {OnOff.cluster_id: ClusterType.Client}}
    )
    with_profile(device)
    recorder = await ButtonEventRecorder.create(device)

    assert recorder.event_types() == {
        "button": ["single_press", "multi_press", "long_press_end"]
    }

    send_command(device, 1, OnOff.cluster_id, "toggle")
    send_command(device, 1, OnOff.cluster_id, "on")
    send_command(device, 1, OnOff.cluster_id, "off")
    # Not a button press
    send_command(device, 1, OnOff.cluster_id, "on_with_recall_global_scene")

    assert recorder.pop() == [
        ("button", "single_press"),
        ("button", "multi_press", {"press_count": 2}),
        ("button", "long_press_end"),
    ]


async def test_snzb01m_button_event_entities(zigpy_device_from_v2_quirk):
    """Test the button event entities of the SNZB-01M remote."""
    device = zigpy_device_from_v2_quirk(
        "SONOFF",
        "SNZB-01M",
        cluster_ids={
            ep: {SonoffButtonCluster.cluster_id: ClusterType.Server}
            for ep in (1, 2, 3, 4)
        },
    )
    with_profile(device)
    recorder = await ButtonEventRecorder.create(device)

    gestures = ["single_press", "multi_press", "long_press_end"]
    assert recorder.event_types() == {
        "button_1": gestures,
        "button_2": gestures,
        "button_3": gestures,
        "button_4": gestures,
    }

    key_action_event = SonoffButtonCluster.AttributeDefs.key_action_event
    for endpoint_id in (1, 2, 3, 4):
        for value in (1, 2, 4, 3, 99):
            report_attribute(
                device,
                endpoint_id,
                SonoffButtonCluster.cluster_id,
                key_action_event,
                value,
            )

    assert recorder.pop() == [
        event
        for button in ("button_1", "button_2", "button_3", "button_4")
        for event in (
            (button, "single_press"),
            (button, "multi_press", {"press_count": 2}),
            (button, "multi_press", {"press_count": 3}),
            (button, "long_press_end"),
        )
    ]
