"""Tests for Third Reality button quirks."""

import pytest

from tests.common import ClusterListener
import zhaquirks
from zhaquirks.thirdreality.button import ThirdRealityButtonCluster

zhaquirks.setup()


@pytest.mark.parametrize(
    "quirk",
    (
        zhaquirks.thirdreality.button.ThirdRealityButton,
    ),  # Replace with actual device quirk class name
)
async def test_third_reality_button(zigpy_device_from_quirk, quirk):
    """Test Third Reality button event conversion and triggering functionality."""
    # Create mock device based on the quirk
    device = zigpy_device_from_quirk(quirk)

    # Get relevant clusters
    multistate_cluster = device.endpoints[1].multistate_input
    private_cluster = device.endpoints[1].in_clusters[
        ThirdRealityButtonCluster.cluster_id
    ]

    # Create cluster listener
    multistate_listener = ClusterListener(multistate_cluster)

    # Test 1: Verify single click event conversion
    multistate_cluster.update_attribute(0x0055, 1)  # 1 corresponds to single click
    assert len(multistate_listener.zha_send_events) == 1
    assert multistate_listener.zha_send_events[0][0] == "single"
    assert multistate_listener.attribute_updates[-1][0] == 0
    assert multistate_listener.attribute_updates[-1][1] == "single"

    # Test 2: Verify double click event conversion
    multistate_cluster.update_attribute(0x0055, 2)  # 2 corresponds to double click
    assert len(multistate_listener.zha_send_events) == 2
    assert multistate_listener.zha_send_events[1][0] == "double"

    # Test 3: Verify hold event conversion
    multistate_cluster.update_attribute(0x0055, 0)  # 0 corresponds to hold
    assert len(multistate_listener.zha_send_events) == 3
    assert multistate_listener.zha_send_events[2][0] == "hold"

    # Test 4: Verify release event conversion
    multistate_cluster.update_attribute(0x0055, 255)  # 255 corresponds to release
    assert len(multistate_listener.zha_send_events) == 4
    assert multistate_listener.zha_send_events[3][0] == "release"

    # Test 5: Verify private cluster attributes
    assert hasattr(private_cluster.attributes, "cancel_bouble_click")
    attr = private_cluster.attributes.cancel_bouble_click
    assert attr.id == 0x0000
    assert attr.type == int  # Corresponds to t.uint8_t
