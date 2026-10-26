"""Tests for Terncy quirks."""

import pytest
from zha.quirks import DEVICE_REGISTRY
from zigpy.zcl import ClusterType

from tests.common import ButtonEventRecorder, send_command
import zhaquirks
from zhaquirks.terncy import MANUFACTURER_SPECIFIC_CLUSTER_ID
from zhaquirks.terncy.pp01 import TerncyAwarenessSwitch
from zhaquirks.terncy.sd01 import TerncyKnobSmartDimmer

zhaquirks.setup()


@pytest.mark.parametrize("quirk", [TerncyAwarenessSwitch, TerncyKnobSmartDimmer])
async def test_button_events(zigpy_device_from_quirk, quirk):
    """Test the button event entity of the Terncy buttons."""
    device = DEVICE_REGISTRY.resolve(zigpy_device_from_quirk(quirk, apply_quirk=False))
    assert isinstance(device, quirk)

    recorder = await ButtonEventRecorder.create(device)
    assert recorder.event_types() == {"button": ["single_press", "multi_press"]}

    for count, presses in enumerate((1, 2, 3, 4, 5, 9), start=10):
        send_command(
            device,
            1,
            MANUFACTURER_SPECIFIC_CLUSTER_ID,
            "click_event",
            count,
            presses,
            cluster_type=ClusterType.Server,
        )

    # Five or more presses are a quintuple press, which has no exact press count
    assert recorder.pop() == [
        ("button", "single_press"),
        ("button", "multi_press", {"press_count": 2}),
        ("button", "multi_press", {"press_count": 3}),
        ("button", "multi_press", {"press_count": 4}),
    ]


async def test_knob_rotation_no_button_events(zigpy_device_from_quirk):
    """Test that turning the knob fires no button events."""
    device = DEVICE_REGISTRY.resolve(
        zigpy_device_from_quirk(TerncyKnobSmartDimmer, apply_quirk=False)
    )
    recorder = await ButtonEventRecorder.create(device)
    zha_events = []
    recorder.zha_device.on_event("zha_event", zha_events.append)

    device.endpoints[1].in_clusters[MANUFACTURER_SPECIFIC_CLUSTER_ID].update_attribute(
        27, 24
    )
    device.endpoints[1].in_clusters[MANUFACTURER_SPECIFIC_CLUSTER_ID].update_attribute(
        27, -12
    )

    assert [event.data["command"] for event in zha_events] == [
        "rotate_right",
        "rotate_left",
    ]
    assert recorder.pop() == []
