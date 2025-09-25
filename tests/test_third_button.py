"""Test the module for the "third button" function to verify the ZHA event capture logic."""

import pytest

import zhaquirks
from zhaquirks.thirdreality.button-v2 import MultistateInputCluster


class MockListener:
    """Simulate listener class for capturing ZHA events."""

    def __init__(self):
        """Initialize listener with empty event list."""
        self.zha_send_events = []

    def zha_send_event(self, action, event_args):
        """Record ZHA events.

        Args:
            action (str): The type of action for the event.
            event_args (dict): Relevant parameters of the event.

        """
        self.zha_send_events.append((action, event_args))


zhaquirks.setup()


@pytest.mark.parametrize(
    "manufacturer, model",
    [("Third Reality, Inc", "3RSB22BZ")],
)
async def test_third_reality_button_v2(zigpy_device_from_v2_quirk, manufacturer, model):
    """Test Third Reality button event conversion and triggering functionality."""
    # Create mock device based on the v2 quirk
    device = zigpy_device_from_v2_quirk(manufacturer, model)

    # Find the MultistateInputCluster
    multistate_cluster = next(
        (
            cluster
            for cluster in device.endpoints[1].in_clusters.values()
            if isinstance(cluster, MultistateInputCluster)
        ),
        None,
    )
    assert multistate_cluster is not None, "MultistateInputCluster not found"

    # Create mock listener and register it with the cluster
    mock_listener = MockListener()
    multistate_cluster.add_listener(mock_listener)

    # Test 1: Verify single click event conversion
    mock_listener.zha_send_events.clear()
    multistate_cluster.update_attribute(0x0055, 1)  # 1 corresponds to single click
    assert len(mock_listener.zha_send_events) == 1
    assert mock_listener.zha_send_events[0][0] == "single"

    # Test 2: Verify double click event conversion
    mock_listener.zha_send_events.clear()
    multistate_cluster.update_attribute(0x0055, 2)  # 2 corresponds to double click
    assert len(mock_listener.zha_send_events) == 1
    assert mock_listener.zha_send_events[0][0] == "double"

    # Test 3: Verify hold event conversion
    mock_listener.zha_send_events.clear()
    multistate_cluster.update_attribute(0x0055, 0)  # 0 corresponds to hold
    assert len(mock_listener.zha_send_events) == 1
    assert mock_listener.zha_send_events[0][0] == "hold"

    # Test 4: Verify release event conversion
    mock_listener.zha_send_events.clear()
    multistate_cluster.update_attribute(0x0055, 255)  # 255 corresponds to release
    assert len(mock_listener.zha_send_events) == 1
    assert mock_listener.zha_send_events[0][0] == "release"
