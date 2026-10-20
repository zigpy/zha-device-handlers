"""Tests for ADEO quirks."""

from zha.quirks import DEVICE_REGISTRY
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import LevelControl, OnOff
from zigpy.zcl.clusters.lighting import Color

from tests.common import ButtonEventRecorder, send_command
import zhaquirks
from zhaquirks.adeo.color_controller import AdeoColorController, AdeoManufacturerCluster

zhaquirks.setup()


async def test_color_controller_button_events(zigpy_device_from_quirk):
    """Test the button event entities of the ADEO color controller."""
    device = DEVICE_REGISTRY.resolve(
        zigpy_device_from_quirk(AdeoColorController, apply_quirk=False)
    )
    assert isinstance(device, AdeoColorController)

    recorder = await ButtonEventRecorder.create(device)
    assert recorder.event_types() == {
        "button_on": ["single_press"],
        "button_off": ["single_press"],
        "button_1": ["single_press"],
        "button_2": ["single_press"],
        "button_3": ["single_press"],
        "button_4": ["single_press"],
    }

    send_command(device, 1, OnOff.cluster_id, "on")
    send_command(device, 1, OnOff.cluster_id, "off")
    assert recorder.pop() == [
        ("button_on", "single_press"),
        ("button_off", "single_press"),
    ]

    # The preset buttons send 0x0A to 0x0D in a manufacturer-specific command
    for tsn, preset in enumerate((0x0A, 0x0B, 0x0C, 0x0D), start=100):
        hdr = foundation.ZCLHeader.cluster(
            tsn=tsn, command_id=0x00, direction=foundation.Direction.Client_to_Server
        )
        device.packet_received(
            t.ZigbeePacket(
                src_ep=1,
                dst_ep=1,
                tsn=tsn,
                profile_id=260,
                cluster_id=AdeoManufacturerCluster.cluster_id,
                data=t.SerializableBytes(hdr.serialize() + bytes([preset, 0x00])),
            )
        )
    assert recorder.pop() == [
        ("button_1", "single_press"),
        ("button_2", "single_press"),
        ("button_3", "single_press"),
        ("button_4", "single_press"),
    ]

    # The buttons around the circle fire nothing
    send_command(device, 1, LevelControl.cluster_id, "step", 0, 26, 5)
    send_command(device, 1, LevelControl.cluster_id, "stop")
    send_command(device, 1, Color.cluster_id, "step_color_temp", 3, 22, 5, 153, 370)
    send_command(device, 1, Color.cluster_id, "step_saturation", 1, 20, 5)
    send_command(device, 1, Color.cluster_id, "step_hue", 3, 20, 5)
    assert recorder.pop() == []
