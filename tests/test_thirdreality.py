"""Tests for Third Reality quirks."""

import itertools
from unittest import mock

import pytest
from zigpy.profiles import zha
import zigpy.types as t
from zigpy.zcl import ClusterType, foundation
from zigpy.zcl.clusters.general import MultistateInput
from zigpy.zcl.clusters.security import IasZone

from tests.common import ButtonEventRecorder, ClusterListener
import zhaquirks
from zhaquirks.thirdreality.button import MultistateInputCluster
import zhaquirks.thirdreality.night_light
import zhaquirks.thirdreality.three_button

zhaquirks.setup()


@pytest.mark.parametrize("quirk", (zhaquirks.thirdreality.night_light.Nightlight,))
async def test_third_reality_nightlight(zigpy_device_from_quirk, quirk):
    """Test Third Reality night light forwarding motion attribute to IasZone cluster."""

    device = zigpy_device_from_quirk(quirk)

    ias_zone_cluster = device.endpoints[1].ias_zone
    ias_zone_listener = ClusterListener(ias_zone_cluster)

    ias_zone_status_id = IasZone.AttributeDefs.zone_status.id

    third_reality_cluster = device.endpoints[1].in_clusters[0xFC00]

    # 0x0002 is also used on manufacturer specific cluster for motion events
    third_reality_cluster.update_attribute(0x0002, IasZone.ZoneStatus.Alarm_1)

    assert len(ias_zone_listener.attribute_updates) == 1
    assert ias_zone_listener.attribute_updates[0][0] == ias_zone_status_id
    assert ias_zone_listener.attribute_updates[0][1] == IasZone.ZoneStatus.Alarm_1

    # turn off motion alarm
    third_reality_cluster.update_attribute(0x0002, 0)

    assert len(ias_zone_listener.attribute_updates) == 2
    assert ias_zone_listener.attribute_updates[1][0] == ias_zone_status_id
    assert ias_zone_listener.attribute_updates[1][1] == 0


@pytest.mark.parametrize(
    ("attr_value", "expected_action"),
    [
        (1, "single"),  # 1 corresponds to single click
        (2, "double"),  # 2 corresponds to double click
        (0, "hold"),  # 0 corresponds to hold
        (255, "release"),  # 255 corresponds to release
    ],
)
@pytest.mark.parametrize(
    ("manufacturer", "model"),
    [("Third Reality, Inc", "3RSB22BZ")],
)
async def test_third_reality_button_v2(
    zigpy_device_from_v2_quirk, manufacturer, model, attr_value, expected_action
):
    """Test Third Reality button event conversion and triggering functionality."""
    device = zigpy_device_from_v2_quirk(manufacturer, model)
    multistate_cluster = device.endpoints[1].in_clusters[
        MultistateInputCluster.cluster_id
    ]

    # Create mock listener and register it with the cluster
    listener = mock.MagicMock()
    multistate_cluster.add_listener(listener)

    multistate_cluster.update_attribute(
        0x0055, attr_value
    )  # 1 corresponds to single click
    assert listener.zha_send_event.call_count == 1
    assert listener.zha_send_event.call_args_list[0] == mock.call(
        expected_action, {"value": attr_value}
    )


@pytest.mark.parametrize(
    ("endpoint_id", "attr_value", "expected_action"),
    [
        (1, 1, "single"),
        (2, 2, "double"),
        (3, 0, "hold"),
    ],
)
async def test_third_reality_three_button_v2_events(
    zigpy_device_from_v2_quirk, endpoint_id, attr_value, expected_action
):
    """Test Third Reality three-button event conversion on all button endpoints."""
    device = zigpy_device_from_v2_quirk(
        "Third Reality, Inc",
        "3RSB01085Z",
        cluster_ids={
            1: {MultistateInput.cluster_id: ClusterType.Server},
            2: {MultistateInput.cluster_id: ClusterType.Server},
            3: {MultistateInput.cluster_id: ClusterType.Server},
        },
    )
    multistate_cluster = device.endpoints[endpoint_id].in_clusters[
        MultistateInput.cluster_id
    ]

    listener = mock.MagicMock()
    multistate_cluster.add_listener(listener)

    multistate_cluster.update_attribute(0x0055, attr_value)
    assert listener.zha_send_event.call_count == 1
    assert listener.zha_send_event.call_args_list[0] == mock.call(
        expected_action, {"value": attr_value}
    )


async def test_third_reality_three_button_v2_ignores_unknown_press_type(
    zigpy_device_from_v2_quirk,
):
    """Test unsupported button press values do not emit events."""
    device = zigpy_device_from_v2_quirk(
        "Third Reality, Inc",
        "3RSB01085Z",
        cluster_ids={
            1: {MultistateInput.cluster_id: ClusterType.Server},
            2: {MultistateInput.cluster_id: ClusterType.Server},
            3: {MultistateInput.cluster_id: ClusterType.Server},
        },
    )
    multistate_cluster = device.endpoints[1].in_clusters[MultistateInput.cluster_id]

    listener = mock.MagicMock()
    multistate_cluster.add_listener(listener)

    multistate_cluster.update_attribute(0x0055, 42)
    assert listener.zha_send_event.call_count == 0


_TSNS = itertools.cycle(range(256))


def report_present_value(device, endpoint_id, value) -> None:
    """Receive a `present_value` report frame from a multistate input cluster."""
    attribute = MultistateInput.AttributeDefs.present_value
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
            cluster_id=MultistateInput.cluster_id,
            data=t.SerializableBytes(header.serialize() + schema([report]).serialize()),
        )
    )


GESTURES = ["single_press", "multi_press", "long_press_start", "long_press_end"]


async def test_third_reality_button_event_entity(zigpy_device_from_v2_quirk):
    """Test the button event entity of the Third Reality button."""
    device = zigpy_device_from_v2_quirk(
        "Third Reality, Inc",
        "3RSB22BZ",
        cluster_ids={1: {MultistateInput.cluster_id: ClusterType.Server}},
    )
    device.endpoints[1].profile_id = zha.PROFILE_ID
    device.endpoints[1].device_type = zha.DeviceType.REMOTE_CONTROL
    recorder = await ButtonEventRecorder.create(device)

    assert recorder.event_types() == {"button": GESTURES}

    # Single, double, hold and release; a release without a hold and 42, which is
    # no press type, fire nothing
    for value in (1, 255, 2, 0, 255, 255, 42):
        report_present_value(device, 1, value)

    assert recorder.pop() == [
        ("button", "single_press"),
        ("button", "multi_press", {"press_count": 2}),
        ("button", "long_press_start"),
        ("button", "long_press_end"),
    ]


async def test_third_reality_three_button_event_entities(zigpy_device_from_v2_quirk):
    """Test the button event entities of the Third Reality three-button remote."""
    device = zigpy_device_from_v2_quirk(
        "Third Reality, Inc",
        "3RSB01085Z",
        cluster_ids={
            ep: {MultistateInput.cluster_id: ClusterType.Server} for ep in (1, 2, 3)
        },
    )
    for endpoint_id in (1, 2, 3):
        device.endpoints[endpoint_id].profile_id = zha.PROFILE_ID
        device.endpoints[endpoint_id].device_type = zha.DeviceType.REMOTE_CONTROL
    recorder = await ButtonEventRecorder.create(device)

    assert recorder.event_types() == {
        "button_1": GESTURES,
        "button_2": GESTURES,
        "button_3": GESTURES,
    }

    for endpoint_id in (1, 2, 3):
        for value in (1, 255, 2, 0, 255, 255, 42):
            report_present_value(device, endpoint_id, value)

    assert recorder.pop() == [
        event
        for button in ("button_1", "button_2", "button_3")
        for event in (
            (button, "single_press"),
            (button, "multi_press", {"press_count": 2}),
            (button, "long_press_start"),
            (button, "long_press_end"),
        )
    ]
