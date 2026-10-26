"""Tests for OSRAM quirks."""

from zha.quirks import DEVICE_REGISTRY
from zigpy.zcl.clusters.general import LevelControl, OnOff
from zigpy.zcl.clusters.lighting import Color

from tests.common import ButtonEventRecorder, send_command
import zhaquirks
from zhaquirks.osram.switchmini import OsramSwitchMini

zhaquirks.setup()


async def test_switch_mini_button_events(zigpy_device_from_quirk):
    """Test the button event entities of the OSRAM Smart+ Switch Mini."""
    device = DEVICE_REGISTRY.resolve(
        zigpy_device_from_quirk(OsramSwitchMini, apply_quirk=False)
    )
    assert isinstance(device, OsramSwitchMini)

    recorder = await ButtonEventRecorder.create(device)
    assert recorder.event_types() == {
        "button_1": ["press_end", "long_press_start", "long_press_end"],
        "button_2": ["press_end", "long_press_start", "long_press_end"],
        "button_3": ["press_end", "long_press_start", "long_press_end"],
    }

    # Up (button 1): on, move_with_on_off and stop on endpoint 1
    send_command(device, 1, OnOff.cluster_id, "on")
    send_command(device, 1, LevelControl.cluster_id, "move_with_on_off", 0, 38)
    send_command(device, 1, LevelControl.cluster_id, "stop")
    # The trigger's stop_with_on_off ends the hold as well
    send_command(device, 1, LevelControl.cluster_id, "move_with_on_off", 0, 38)
    send_command(device, 1, LevelControl.cluster_id, "stop_with_on_off")
    assert recorder.pop() == [
        ("button_1", "press_end"),
        ("button_1", "long_press_start"),
        ("button_1", "long_press_end"),
        ("button_1", "long_press_start"),
        ("button_1", "long_press_end"),
    ]

    # Circle (button 2): move_to_level_with_on_off, move_to_saturation and
    # move_hue on endpoint 3
    send_command(
        device, 3, LevelControl.cluster_id, "move_to_level_with_on_off", 254, 10
    )
    send_command(device, 3, Color.cluster_id, "move_to_saturation", 254, 2)
    send_command(device, 3, Color.cluster_id, "move_hue", 0, 0)
    assert recorder.pop() == [
        ("button_2", "press_end"),
        ("button_2", "long_press_start"),
        ("button_2", "long_press_end"),
    ]

    # Down (button 3): off, move and stop on endpoint 2
    send_command(device, 2, OnOff.cluster_id, "off")
    send_command(device, 2, LevelControl.cluster_id, "move", 1, 38)
    send_command(device, 2, LevelControl.cluster_id, "stop")
    assert recorder.pop() == [
        ("button_3", "press_end"),
        ("button_3", "long_press_start"),
        ("button_3", "long_press_end"),
    ]

    # Other commands fire nothing
    send_command(device, 3, Color.cluster_id, "move_to_color_temp", 370, 10)
    send_command(device, 1, OnOff.cluster_id, "off")
    send_command(device, 2, OnOff.cluster_id, "on")
    assert recorder.pop() == []
