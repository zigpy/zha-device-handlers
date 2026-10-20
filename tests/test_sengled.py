"""Tests for Sengled quirks."""

from zha.quirks import DEVICE_REGISTRY

from tests.common import ButtonEventRecorder, send_command
import zhaquirks
from zhaquirks.sengled.e1e_g7f import (
    SengledE1EG7F,
    SengledE1EG7FManufacturerSpecificCluster,
)

zhaquirks.setup()

SENGLED_MANUFACTURER_CODE = 0x1160


async def test_e1e_g7f_button_events(zigpy_device_from_quirk):
    """Test the button event entities of the Sengled E1E-G7F."""
    device = DEVICE_REGISTRY.resolve(
        zigpy_device_from_quirk(SengledE1EG7F, apply_quirk=False)
    )
    assert isinstance(device, SengledE1EG7F)

    recorder = await ButtonEventRecorder.create(device)
    assert recorder.event_types() == {
        "button_on": ["single_press", "multi_press", "long_press_end"],
        "button_dim_up": ["press_start", "long_press_start"],
        "button_dim_down": ["press_start", "long_press_start"],
        "button_off": ["single_press", "multi_press", "long_press_end"],
    }

    def press(button: int, press_type: int = 0) -> None:
        send_command(
            device,
            1,
            SengledE1EG7FManufacturerSpecificCluster.cluster_id,
            "command",
            button,
            0,
            press_type,
            0,
            manufacturer=SENGLED_MANUFACTURER_CODE,
        )

    # On (1, double 5, long 6) and off (4, double 7, long 8)
    for button, suffix in ((1, "button_on"), (4, "button_off")):
        double, long = (5, 6) if button == 1 else (7, 8)
        press(button)
        press(double)
        press(long)
        assert recorder.pop() == [
            (suffix, "single_press"),
            (suffix, "multi_press", {"press_count": 2}),
            (suffix, "long_press_end"),
        ]

    # Up (2) and down (3): the press, then the repeated hold
    for button, suffix in ((2, "button_dim_up"), (3, "button_dim_down")):
        press(button, 1)
        press(button, 1)
        press(button, 2)
        press(button, 2)
        press(button, 2)
        press(button, 1)
        press(button, 2)
        assert recorder.pop() == [
            (suffix, "press_start"),
            (suffix, "press_start"),
            (suffix, "long_press_start"),
            (suffix, "press_start"),
            (suffix, "long_press_start"),
        ]

    # Unknown buttons fire nothing
    press(9)
    assert recorder.pop() == []
