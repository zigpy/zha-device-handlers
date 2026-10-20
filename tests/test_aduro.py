"""Tests for AduroSmart quirks."""

from zha.quirks import DEVICE_REGISTRY
from zigpy.zcl.clusters.general import LevelControl, OnOff

from tests.common import ButtonEventRecorder, send_command
import zhaquirks
from zhaquirks.aduro.adurolightncc import AdurolightNCC

zhaquirks.setup()


async def test_adurolight_ncc_button_events(zigpy_device_from_quirk):
    """Test the button event entities of the Adurolight NCC remote."""
    device = DEVICE_REGISTRY.resolve(
        zigpy_device_from_quirk(AdurolightNCC, apply_quirk=False)
    )
    assert isinstance(device, AdurolightNCC)

    recorder = await ButtonEventRecorder.create(device)
    assert recorder.event_types() == {
        "button_on": ["single_press"],
        "button_dim_up": ["single_press"],
        "button_dim_down": ["single_press"],
        "button_off": ["single_press"],
    }

    send_command(device, 1, OnOff.cluster_id, "on")
    send_command(device, 1, LevelControl.cluster_id, "step", 0, 32, 5)
    send_command(device, 1, LevelControl.cluster_id, "step", 1, 32, 5)
    send_command(device, 1, OnOff.cluster_id, "off")
    assert recorder.pop() == [
        ("button_on", "single_press"),
        ("button_dim_up", "single_press"),
        ("button_dim_down", "single_press"),
        ("button_off", "single_press"),
    ]

    # Other commands fire nothing
    send_command(device, 1, OnOff.cluster_id, "toggle")
    send_command(device, 1, LevelControl.cluster_id, "move", 0, 32)
    assert recorder.pop() == []
