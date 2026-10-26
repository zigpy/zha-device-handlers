"""Tests for Sourcing & Creation quirks."""

from zha.quirks import DEVICE_REGISTRY
from zigpy.zcl.clusters.general import LevelControl, OnOff
from zigpy.zcl.clusters.lighting import Color

from tests.common import ButtonEventRecorder, send_command
import zhaquirks
from zhaquirks.sourcingandcreation.smart_button import SourcingAndCreationSmartButton

zhaquirks.setup()


async def test_smart_button_button_events(zigpy_device_from_quirk):
    """Test the button event entity of the EB-SB-1B smart button."""
    device = DEVICE_REGISTRY.resolve(
        zigpy_device_from_quirk(SourcingAndCreationSmartButton, apply_quirk=False)
    )
    assert isinstance(device, SourcingAndCreationSmartButton)

    recorder = await ButtonEventRecorder.create(device)
    assert recorder.event_types() == {
        "button": ["single_press", "multi_press", "long_press_start", "long_press_end"]
    }

    send_command(device, 1, OnOff.cluster_id, "on")
    send_command(device, 1, OnOff.cluster_id, "off")
    send_command(device, 1, Color.cluster_id, "step_color_temp", 1, 50, 5, 153, 370)
    send_command(device, 1, LevelControl.cluster_id, "step", 0, 50, 5)
    send_command(device, 1, LevelControl.cluster_id, "step", 0, 50, 5)
    send_command(device, 1, LevelControl.cluster_id, "stop")

    assert recorder.pop() == [
        ("button", "single_press"),
        ("button", "single_press"),
        ("button", "multi_press", {"press_count": 2}),
        ("button", "long_press_start"),
        ("button", "long_press_end"),
    ]

    # A stop without a hold is not classified
    send_command(device, 1, LevelControl.cluster_id, "stop")
    assert recorder.pop() == []
