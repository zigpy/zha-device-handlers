"""Tests for the SONOFF MINI-ZB2GS and MINI-ZB2GS-L devices."""

from unittest import mock

import pytest
from zigpy.zcl import ClusterType, foundation
from zigpy.zcl.clusters.general import OnOff as OnOffCluster

from tests.common import ClusterListener
import zhaquirks
from zhaquirks.const import CLUSTER_ID, COMMAND, ENDPOINT_ID
from zhaquirks.sonoff.mini_zb2gs import (
    RELAY_DETACH_ATTR_ID,
    OnOff,
    RelaySperaKeyAction,
    SonoffCluster,
)

zhaquirks.setup()

MODELS = ["MINI-ZB2GS-L", "MINI-ZB2GS"]

# the quirks replace the sonoff cluster on both endpoints and every OnOff instance
DEVICE_CLUSTERS = {
    1: {
        OnOffCluster.cluster_id: ClusterType.Server,
        SonoffCluster.cluster_id: ClusterType.Server,
    },
    2: {
        OnOffCluster.cluster_id: ClusterType.Server,
        SonoffCluster.cluster_id: ClusterType.Server,
    },
}

SWITCH_ACTIONS = {
    "Single Click": RelaySperaKeyAction.Single_click,
    "Double Click": RelaySperaKeyAction.Double_click,
    "Long Press": RelaySperaKeyAction.Long_press,
    "Follow On": RelaySperaKeyAction.Follow_on,
    "Follow Off": RelaySperaKeyAction.Follow_off,
}


def expected_triggers():
    """Return the device automation triggers both models are expected to expose."""
    return {
        (f"External Switch {endpoint_id} action", action): {
            CLUSTER_ID: SonoffCluster.cluster_id,
            ENDPOINT_ID: endpoint_id,
            COMMAND: key_action.name,
        }
        for endpoint_id in (1, 2)
        for action, key_action in SWITCH_ACTIONS.items()
    }


@pytest.mark.parametrize("model", MODELS)
def test_zb2gs_cluster_replacement(zigpy_device_from_v2_quirk, model):
    """The custom clusters are installed on both endpoints of both models."""
    device = zigpy_device_from_v2_quirk("SONOFF", model, cluster_ids=DEVICE_CLUSTERS)

    for endpoint_id in (1, 2):
        endpoint = device.endpoints[endpoint_id]
        assert isinstance(endpoint.in_clusters[SonoffCluster.cluster_id], SonoffCluster)
        assert isinstance(endpoint.on_off, OnOff)


@pytest.mark.parametrize("model", MODELS)
def test_zb2gs_device_automation_triggers(zigpy_device_from_v2_quirk, model):
    """Follow on/off actions are exposed as device automation triggers."""
    device = zigpy_device_from_v2_quirk("SONOFF", model, cluster_ids=DEVICE_CLUSTERS)

    assert device.device_automation_triggers == expected_triggers()


@pytest.mark.parametrize(
    ("key_action", "expected_command"),
    [
        (RelaySperaKeyAction.Single_click, "Single_click"),
        (RelaySperaKeyAction.Double_click, "Double_click"),
        (RelaySperaKeyAction.Long_press, "Long_press"),
        (RelaySperaKeyAction.Follow_on, "Follow_on"),
        (RelaySperaKeyAction.Follow_off, "Follow_off"),
    ],
    ids=["single", "double", "long", "follow_on", "follow_off"],
)
@pytest.mark.parametrize("endpoint_id", [1, 2])
def test_zb2gs_key_action_events(
    zigpy_device_from_v2_quirk, endpoint_id, key_action, expected_command
):
    """Every key action is converted into a matching ZHA event."""
    device = zigpy_device_from_v2_quirk(
        "SONOFF", "MINI-ZB2GS-L", cluster_ids=DEVICE_CLUSTERS
    )

    cluster = device.endpoints[endpoint_id].in_clusters[SonoffCluster.cluster_id]
    event_listener = mock.MagicMock()
    cluster.add_listener(event_listener)
    attribute_listener = ClusterListener(cluster)

    cluster.update_attribute(RELAY_DETACH_ATTR_ID, key_action)

    assert attribute_listener.attribute_updates == [
        (RELAY_DETACH_ATTR_ID, expected_command)
    ]
    event_listener.zha_send_event.assert_called_once_with(expected_command, {})


def test_zb2gs_unknown_key_action_value(zigpy_device_from_v2_quirk):
    """Unknown key action values fall back to the enum's undefined member."""
    device = zigpy_device_from_v2_quirk(
        "SONOFF", "MINI-ZB2GS-L", cluster_ids=DEVICE_CLUSTERS
    )

    cluster = device.endpoints[1].in_clusters[SonoffCluster.cluster_id]
    event_listener = mock.MagicMock()
    cluster.add_listener(event_listener)

    cluster.update_attribute(RELAY_DETACH_ATTR_ID, 0x99)

    event_listener.zha_send_event.assert_called_once_with("undefined_0x99", {})


def test_zb2gs_other_attribute_update_does_not_emit_event(
    zigpy_device_from_v2_quirk,
):
    """Only the detached relay attribute is forwarded as a ZHA event."""
    device = zigpy_device_from_v2_quirk(
        "SONOFF", "MINI-ZB2GS-L", cluster_ids=DEVICE_CLUSTERS
    )

    cluster = device.endpoints[1].in_clusters[SonoffCluster.cluster_id]
    event_listener = mock.MagicMock()
    cluster.add_listener(event_listener)

    cluster.update_attribute(
        SonoffCluster.AttributeDefs.network_led.id,
        SonoffCluster.AttributeDefs.network_led.type.true,
    )

    assert event_listener.zha_send_event.call_count == 0


@pytest.mark.parametrize("endpoint_id", [1, 2])
async def test_zb2gs_toggle_maps_to_single_click(
    zigpy_device_from_v2_quirk, endpoint_id
):
    """A toggle command from the gateway is reported as a single click event."""
    device = zigpy_device_from_v2_quirk(
        "SONOFF", "MINI-ZB2GS-L", cluster_ids=DEVICE_CLUSTERS
    )

    on_off_cluster = device.endpoints[endpoint_id].on_off
    sonoff_cluster = device.endpoints[endpoint_id].in_clusters[SonoffCluster.cluster_id]
    event_listener = mock.MagicMock()
    sonoff_cluster.add_listener(event_listener)

    hdr = foundation.ZCLHeader.cluster(
        tsn=1, command_id=OnOffCluster.ServerCommandDefs.toggle.id
    )
    on_off_cluster.handle_cluster_request(hdr, [])

    assert sonoff_cluster.get(RELAY_DETACH_ATTR_ID) == "Single_click"
    event_listener.zha_send_event.assert_called_once_with("Single_click", {})


@pytest.mark.parametrize(
    "command_id",
    [OnOffCluster.ServerCommandDefs.off.id, OnOffCluster.ServerCommandDefs.on.id],
    ids=["off", "on"],
)
async def test_zb2gs_non_toggle_command_does_not_emit_event(
    zigpy_device_from_v2_quirk, command_id
):
    """Commands other than toggle do not create key action events."""
    device = zigpy_device_from_v2_quirk(
        "SONOFF", "MINI-ZB2GS-L", cluster_ids=DEVICE_CLUSTERS
    )

    on_off_cluster = device.endpoints[1].on_off
    sonoff_cluster = device.endpoints[1].in_clusters[SonoffCluster.cluster_id]
    event_listener = mock.MagicMock()
    sonoff_cluster.add_listener(event_listener)

    hdr = foundation.ZCLHeader.cluster(tsn=1, command_id=command_id)
    on_off_cluster.handle_cluster_request(hdr, [])

    assert event_listener.zha_send_event.call_count == 0
