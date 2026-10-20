"""Tests for Aurora quirks."""

from zha.quirks import DEVICE_REGISTRY
from zigpy.zcl.clusters.general import LevelControl, OnOff
from zigpy.zcl.clusters.lighting import Color

from tests.common import ButtonEventRecorder, send_command
import zhaquirks
from zhaquirks.aurora.aurora_dimmer import AuroraDimmerBatteryPowered

zhaquirks.setup()


async def test_battery_dimmer_button_events(zigpy_device_from_quirk):
    """Test the button event entities of the Aurora battery rotary dimmer."""
    device = DEVICE_REGISTRY.resolve(
        zigpy_device_from_quirk(AuroraDimmerBatteryPowered, apply_quirk=False)
    )
    assert isinstance(device, AuroraDimmerBatteryPowered)

    recorder = await ButtonEventRecorder.create(device)
    assert recorder.event_types() == {
        "button_right": ["single_press"],
        "button_left": ["single_press"],
    }

    # Pressing a knob toggles between on and off
    for endpoint_id, suffix in ((1, "button_right"), (2, "button_left")):
        send_command(device, endpoint_id, OnOff.cluster_id, "on")
        send_command(device, endpoint_id, OnOff.cluster_id, "off")
        assert recorder.pop() == [(suffix, "single_press"), (suffix, "single_press")]

    # Turning a knob fires nothing
    send_command(device, 1, LevelControl.cluster_id, "step", 0, 10, 0)
    send_command(device, 2, LevelControl.cluster_id, "step", 1, 10, 0)
    send_command(device, 1, Color.cluster_id, "step_color_temp", 3, 10, 0, 0, 0)
    assert recorder.pop() == []
