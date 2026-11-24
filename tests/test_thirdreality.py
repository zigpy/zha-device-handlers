"""Tests for Third Reality quirks."""

from unittest import mock

import pytest
from zha.application import Platform
from zha.application.platforms import ZclPlatformEntity
from zha.quirks import DEVICE_REGISTRY
from zha.zigbee.child_device import DEVICE_LEVEL_CLUSTERS, ChildDevice
from zigpy.zcl import ClusterType
from zigpy.zcl.clusters.general import MultistateInput
from zigpy.zcl.clusters.security import IasZone

from tests.common import ClusterListener
from tests.zha_helpers import join_device_from_diagnostics, zha_gateway
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


@pytest.mark.parametrize(
    ("diagnostics", "child_device_ids"),
    [
        ("third-reality-inc-3rdp01072z-0x00000036.json", ("left", "right")),
        ("third-reality-inc-3rwp01073z-0x00000036.json", ("bottom", "top")),
    ],
)
async def test_third_reality_dual_plug_child_devices(diagnostics, child_device_ids):
    """Test each outlet of the dual plugs is a child device."""
    async with zha_gateway() as gateway:
        device = await join_device_from_diagnostics(
            gateway, diagnostics, DEVICE_REGISTRY
        )

        first, second = child_device_ids
        assert device.child_devices == {
            first: ChildDevice(
                id=first,
                endpoint_ids=frozenset({1}),
                translation_key=first,
                fallback_name=first.capitalize(),
            ),
            second: ChildDevice(
                id=second,
                endpoint_ids=frozenset({2}),
                translation_key=second,
                fallback_name=second.capitalize(),
            ),
        }

        for entity in device.platform_entities.values():
            if entity.PLATFORM == Platform.VIRTUAL:
                continue

            if (
                isinstance(entity, ZclPlatformEntity)
                and entity.cluster.cluster_id not in DEVICE_LEVEL_CLUSTERS
            ):
                # Everything of an outlet, including its meter and its settings
                expected = child_device_ids[entity.endpoint.id - 1]
            else:
                # The LED brightness (Basic), identify, firmware and signal strength
                expected = None

            assert entity.state.child_device_id == expected, entity

        # The outlets' entities have the same names, the child device tells them apart
        for unique_id_suffix, translation_key in (
            ("reset_summation_delivered", "reset_total_energy"),
            ("on_to_off_delay", "countdown_to_turn_off"),
            ("off_to_on_delay", "countdown_to_turn_on"),
        ):
            entities = [
                entity
                for entity in device.platform_entities.values()
                if entity.unique_id.endswith(f"-{unique_id_suffix}")
            ]
            assert len(entities) == 2
            assert {entity.translation_key for entity in entities} == {translation_key}

        # The outlet's switch is the primary entity of its child device
        switches = [
            entity
            for entity in device.platform_entities.values()
            if entity.PLATFORM == Platform.SWITCH and entity.primary
        ]
        assert sorted(entity.state.child_device_id for entity in switches) == sorted(
            child_device_ids
        )
        assert device.primary_entity is None
