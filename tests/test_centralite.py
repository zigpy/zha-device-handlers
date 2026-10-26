"""Tests for CentraLite quirks."""

from zha.quirks import DEVICE_REGISTRY
from zigpy.zcl.clusters.general import LevelControl, OnOff

from tests.common import ButtonEventRecorder, send_command
import zhaquirks
from zhaquirks.centralite.cl_3130 import CentraLite3130
from zhaquirks.centralite.cl_3460L import CentraLite3460L
from zhaquirks.centralite.motionandtemp import CentraLite3450L

zhaquirks.setup()


async def test_3130_button_events(zigpy_device_from_quirk):
    """Test the button event entities of the CentraLite 3130 dimming switch."""
    device = DEVICE_REGISTRY.resolve(
        zigpy_device_from_quirk(CentraLite3130, apply_quirk=False)
    )
    assert isinstance(device, CentraLite3130)

    recorder = await ButtonEventRecorder.create(device)
    assert recorder.event_types() == {
        "button_up": ["press_end", "long_press_start", "long_press_end"],
        "button_down": ["press_end", "long_press_start", "long_press_end"],
    }

    send_command(device, 1, OnOff.cluster_id, "on")
    send_command(device, 1, OnOff.cluster_id, "off")
    send_command(
        device, 1, LevelControl.cluster_id, "move_with_on_off", 0, 50
    )  # hold up
    send_command(device, 1, LevelControl.cluster_id, "stop")
    send_command(device, 1, LevelControl.cluster_id, "move", 1, 50)  # hold down
    send_command(device, 1, LevelControl.cluster_id, "stop")

    assert recorder.pop() == [
        ("button_up", "press_end"),
        ("button_down", "press_end"),
        ("button_up", "long_press_start"),
        ("button_up", "long_press_end"),
        ("button_down", "long_press_start"),
        ("button_down", "long_press_end"),
    ]

    # The stop with on/off ends the hold as well, and only for the held button
    send_command(device, 1, LevelControl.cluster_id, "move_with_on_off", 0, 50)
    send_command(device, 1, LevelControl.cluster_id, "stop_with_on_off")
    send_command(device, 1, LevelControl.cluster_id, "move", 1, 50)
    send_command(device, 1, LevelControl.cluster_id, "stop")

    assert recorder.pop() == [
        ("button_up", "long_press_start"),
        ("button_up", "long_press_end"),
        ("button_down", "long_press_start"),
        ("button_down", "long_press_end"),
    ]

    # A stop without a hold is not classified
    send_command(device, 1, LevelControl.cluster_id, "stop")
    send_command(device, 1, LevelControl.cluster_id, "stop_with_on_off")
    send_command(device, 1, OnOff.cluster_id, "toggle")
    assert recorder.pop() == []


async def test_3460l_button_events(zigpy_device_from_quirk):
    """Test the button event entity of the CentraLite 3460-L smart button."""
    device = DEVICE_REGISTRY.resolve(
        zigpy_device_from_quirk(CentraLite3460L, apply_quirk=False)
    )
    assert isinstance(device, CentraLite3460L)

    recorder = await ButtonEventRecorder.create(device)
    assert recorder.event_types() == {"button": ["press_start", "press_end"]}

    send_command(device, 1, OnOff.cluster_id, "on")
    send_command(device, 1, OnOff.cluster_id, "off")
    send_command(device, 1, OnOff.cluster_id, "toggle")

    assert recorder.pop() == [("button", "press_start"), ("button", "press_end")]


async def test_3450l_button_events(zigpy_device_from_quirk):
    """Test the button event entities of the CentraLite 3450-L key fob."""
    device = DEVICE_REGISTRY.resolve(
        zigpy_device_from_quirk(CentraLite3450L, apply_quirk=False)
    )
    assert isinstance(device, CentraLite3450L)

    recorder = await ButtonEventRecorder.create(device)
    assert recorder.event_types() == {
        f"button_{endpoint_id}": ["press_start", "press_end"]
        for endpoint_id in (1, 2, 3, 4)
    }

    for endpoint_id in (1, 2, 3, 4):
        send_command(device, endpoint_id, OnOff.cluster_id, "on")
        send_command(device, endpoint_id, OnOff.cluster_id, "off")
        send_command(device, endpoint_id, OnOff.cluster_id, "toggle")

        assert recorder.pop() == [
            (f"button_{endpoint_id}", "press_start"),
            (f"button_{endpoint_id}", "press_end"),
        ]
