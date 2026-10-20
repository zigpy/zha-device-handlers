"""Tests for Sunricher quirks."""

from zigpy.profiles import zha
from zigpy.zcl import ClusterType
from zigpy.zcl.clusters.general import LevelControl, OnOff

from tests.common import ButtonEventRecorder, send_command
import zhaquirks

zhaquirks.setup()


async def test_zgrc_key_004_button_events(zigpy_device_from_v2_quirk):
    """Test the button event entities of the Sunricher ZGRC-KEY-004."""
    device = zigpy_device_from_v2_quirk(
        "Sunricher",
        "ZGRC-KEY-004",
        cluster_ids={
            1: {
                OnOff.cluster_id: ClusterType.Client,
                LevelControl.cluster_id: ClusterType.Client,
            }
        },
    )
    device.endpoints[1].profile_id = zha.PROFILE_ID
    device.endpoints[1].device_type = zha.DeviceType.NON_COLOR_SCENE_CONTROLLER

    recorder = await ButtonEventRecorder.create(device)
    assert recorder.event_types() == {
        "button_on": ["press_end", "long_press_start", "long_press_end"],
        "button_off": ["press_end", "long_press_start", "long_press_end"],
    }

    up = LevelControl.MoveMode.Up
    down = LevelControl.MoveMode.Down

    # a stop before a hold is not classified
    send_command(device, 1, LevelControl.cluster_id, "stop_with_on_off")
    send_command(device, 1, OnOff.cluster_id, "on")
    send_command(device, 1, OnOff.cluster_id, "off")
    send_command(device, 1, LevelControl.cluster_id, "move_with_on_off", up, 50)
    send_command(device, 1, LevelControl.cluster_id, "stop_with_on_off")
    send_command(device, 1, LevelControl.cluster_id, "move_with_on_off", down, 50)
    send_command(device, 1, LevelControl.cluster_id, "stop_with_on_off")
    send_command(device, 1, OnOff.cluster_id, "toggle")

    assert recorder.pop() == [
        ("button_on", "press_end"),
        ("button_off", "press_end"),
        ("button_on", "long_press_start"),
        ("button_on", "long_press_end"),
        ("button_off", "long_press_start"),
        ("button_off", "long_press_end"),
    ]
