"""Tests for Lutron quirks."""

from zha.quirks import DEVICE_REGISTRY
from zigpy.zcl.clusters.general import LevelControl

from tests.common import ButtonEventRecorder, send_command
import zhaquirks
from zhaquirks.lutron.lzl4bwhl01remote import LutronLZL4BWHL01Remote

zhaquirks.setup()


async def test_lzl4bwhl01_button_events(zigpy_device_from_quirk):
    """Test the button event entities of the Lutron connected bulb remote."""
    device = DEVICE_REGISTRY.resolve(
        zigpy_device_from_quirk(LutronLZL4BWHL01Remote, apply_quirk=False)
    )
    assert isinstance(device, LutronLZL4BWHL01Remote)

    recorder = await ButtonEventRecorder.create(device)
    assert recorder.event_types() == {
        "button_on": ["single_press"],
        "button_off": ["single_press"],
    }

    level = LevelControl.cluster_id
    send_command(device, 1, level, "move_to_level_with_on_off", 254, 4)
    send_command(device, 1, level, "move_to_level_with_on_off", 0, 4)

    assert recorder.pop() == [
        ("button_on", "single_press"),
        ("button_off", "single_press"),
    ]

    # Other levels and the dim buttons fire nothing
    send_command(device, 1, level, "move_to_level_with_on_off", 128, 4)
    send_command(device, 1, level, "step_with_on_off", 0, 26, 7)
    send_command(device, 1, level, "step", 1, 26, 7)
    send_command(device, 1, level, "stop")
    assert recorder.pop() == []
