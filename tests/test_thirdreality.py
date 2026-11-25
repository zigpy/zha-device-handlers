"""Tests for Third Reality quirks."""

from unittest import mock

import pytest
from zha.application import Platform
from zha.quirks import DEVICE_REGISTRY
from zigpy.zcl import ClusterType, foundation
from zigpy.zcl.clusters.general import MultistateInput
from zigpy.zcl.clusters.security import IasZone

from tests.common import ClusterListener
from tests.zha_helpers import join_device_from_diagnostics, zha_gateway
import zhaquirks
from zhaquirks.thirdreality.button import MultistateInputCluster
from zhaquirks.thirdreality.night_light import (
    LOCAL_ROUTINE_OFF,
    LOCAL_ROUTINE_ON,
    ThirdRealitySpecificCluster,
)
import zhaquirks.thirdreality.three_button

zhaquirks.setup()


async def test_third_reality_nightlight(zigpy_device_from_v2_quirk):
    """Test Third Reality night light forwarding motion attribute to IasZone cluster."""

    device = zigpy_device_from_v2_quirk(
        "Third Reality, Inc",
        "3RSNL02043Z",
        cluster_ids={1: {ThirdRealitySpecificCluster.cluster_id: ClusterType.Server}},
    )

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


async def test_third_reality_nightlight_entities():
    """Test the local routine switch and numbers on the Third Reality night light."""
    async with zha_gateway() as gateway:
        device = await join_device_from_diagnostics(
            gateway, "third-reality-inc-3rsnl02043z-0x00000056.json", DEVICE_REGISTRY
        )
        ieee = str(device.ieee)

        switch = device.get_platform_entity(
            Platform.SWITCH, unique_id=f"{ieee}-1-present_value"
        )
        routine_time = device.get_platform_entity(
            Platform.NUMBER, unique_id=f"{ieee}-1-local_routine_time"
        )
        lux_threshold = device.get_platform_entity(
            Platform.NUMBER, unique_id=f"{ieee}-1-lux_threshold"
        )

        assert routine_time.native_value == 120
        assert lux_threshold.native_value == 5

        # the routine was disabled when the diagnostics were taken
        assert switch.is_on is False

        multistate_input = device.device.endpoints[1].multistate_input
        for value, expected in ((LOCAL_ROUTINE_ON, True), (LOCAL_ROUTINE_OFF, False)):
            multistate_input.update_attribute(
                MultistateInput.AttributeDefs.present_value.id, value
            )
            assert switch.is_on is expected

        multistate_input._write_attributes = mock.AsyncMock(
            return_value=[
                [foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)]
            ]
        )

        await switch.async_turn_on()
        await switch.async_turn_off()

        written = [
            call.args[0][0].value.value
            for call in multistate_input._write_attributes.mock_calls
        ]
        assert written == [LOCAL_ROUTINE_ON, LOCAL_ROUTINE_OFF]


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
