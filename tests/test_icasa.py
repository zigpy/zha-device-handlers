"""Tests for icasa quirks."""

import pytest
from zha.quirks import DEVICE_REGISTRY
from zigpy.zcl.clusters.general import LevelControl, OnOff, Scenes

from tests.common import ButtonEventRecorder, send_command
import zhaquirks
from zhaquirks.icasa.iczb_kpd12 import IcasaKPD12
from zhaquirks.icasa.iczb_kpd14s import IcasaKPD14S
from zhaquirks.icasa.iczb_kpd18s import IcasaKPD18S

zhaquirks.setup()

ON_OFF_EVENT_TYPES = ["press_end", "long_press_start", "long_press_end"]


@pytest.mark.parametrize(
    "quirk, scene_buttons",
    [(IcasaKPD12, 0), (IcasaKPD14S, 2), (IcasaKPD18S, 6)],
)
async def test_keypad_button_events(zigpy_device_from_quirk, quirk, scene_buttons):
    """Test the button event entities of the icasa keypads."""
    device = DEVICE_REGISTRY.resolve(zigpy_device_from_quirk(quirk, apply_quirk=False))
    assert isinstance(device, quirk)

    recorder = await ButtonEventRecorder.create(device)
    assert recorder.event_types() == {
        "button_on": ON_OFF_EVENT_TYPES,
        "button_off": ON_OFF_EVENT_TYPES,
        **{
            f"button_{number}": ["press_end", "long_press_end"]
            for number in range(1, scene_buttons + 1)
        },
    }

    send_command(device, 1, OnOff.cluster_id, "on")
    send_command(device, 1, OnOff.cluster_id, "off")
    send_command(device, 1, LevelControl.cluster_id, "move_with_on_off", 0, 50)
    send_command(device, 1, LevelControl.cluster_id, "stop")
    send_command(device, 1, LevelControl.cluster_id, "move_with_on_off", 1, 50)
    send_command(device, 1, LevelControl.cluster_id, "stop_with_on_off")

    assert recorder.pop() == [
        ("button_on", "press_end"),
        ("button_off", "press_end"),
        ("button_on", "long_press_start"),
        ("button_on", "long_press_end"),
        ("button_off", "long_press_start"),
        ("button_off", "long_press_end"),
    ]

    # The off button may move down without on/off; a plain move up is no button
    send_command(device, 1, LevelControl.cluster_id, "move", 1, 50)
    send_command(device, 1, LevelControl.cluster_id, "stop")
    send_command(device, 1, LevelControl.cluster_id, "move", 0, 50)

    assert recorder.pop() == [
        ("button_off", "long_press_start"),
        ("button_off", "long_press_end"),
    ]

    # A stop without a hold is not classified
    send_command(device, 1, LevelControl.cluster_id, "stop")
    assert recorder.pop() == []

    for number in range(1, scene_buttons + 1):
        send_command(device, 1, Scenes.cluster_id, "recall", 0x0000, number)
        send_command(device, 1, Scenes.cluster_id, "store", 0x0000, number)

        assert recorder.pop() == [
            (f"button_{number}", "press_end"),
            (f"button_{number}", "long_press_end"),
        ]

    # Scenes without a button
    send_command(device, 1, Scenes.cluster_id, "recall", 0x0000, scene_buttons + 1)
    send_command(device, 1, Scenes.cluster_id, "recall", 0x1234, 1)
    assert recorder.pop() == []
