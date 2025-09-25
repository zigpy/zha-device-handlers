"""Tests for Third Reality button quirks."""

import pytest

import zhaquirks
from zhaquirks.thirdreality.button_v2 import (
    MultistateInputCluster,
    ThirdRealityButtonCluster,
)

zhaquirks.setup()


@pytest.mark.parametrize("manufacturer, model", [("Third Reality, Inc", "3RSB22BZ")])
async def test_third_reality_button_v2(zigpy_device_from_v2_quirk, manufacturer, model):
    """Test Third Reality button v2 event conversion and triggering functionality."""

    device = zigpy_device_from_v2_quirk(manufacturer, model)

    multistate_cluster = None
    for cluster in device.endpoints[1].in_clusters.values():
        if isinstance(cluster, MultistateInputCluster):
            multistate_cluster = cluster
            break

    assert multistate_cluster is not None, "MultistateInputCluster not found"

    class MockListener:
        def __init__(self):
            self.events = []

        def zha_send_event(self, cluster, command, args):
            self.events.append((command, args))

    mock_listener = MockListener()
    multistate_cluster.add_listener(mock_listener)

    test_values = [
        (0, "command_hold"),  # HOLD
        (1, "command_single"),  # SINGLE
        (2, "command_double"),  # DOUBLE
        (255, "command_release"),  # RELEASE
    ]

    for value, expected_command in test_values:
        mock_listener.events = []

        multistate_cluster._update_attribute(0x0055, value)

        assert len(mock_listener.events) == 1
        assert mock_listener.events[0][0] == expected_command
        assert mock_listener.events[0][1]["value"] == value

    private_cluster = None
    for cluster in device.endpoints[1].in_clusters.values():
        if isinstance(cluster, ThirdRealityButtonCluster):
            private_cluster = cluster
            break

    assert private_cluster is not None, "ThirdRealityButtonCluster not found"
    assert private_cluster.cluster_id == 0xFF01
    assert hasattr(private_cluster.AttributeDefs, "cancel_bouble_click")
    assert private_cluster.AttributeDefs.cancel_bouble_click.id == 0x0000
