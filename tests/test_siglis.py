"""Tests for Siglis quirks."""

import pytest
from zha.quirks import DEVICE_REGISTRY
import zigpy.types as t
from zigpy.zcl import foundation

from tests.common import ButtonEventRecorder
import zhaquirks
from zhaquirks.siglis.zigfred import (
    SIGLIS_MANUFACTURER_CODE,
    ZIGFRED_CLUSTER_COMMAND_BUTTON_EVENT,
    ZIGFRED_CLUSTER_ID,
    ZigfredPlus,
    ZigfredUno,
)

zhaquirks.setup()

RELEASE = 0
CLICK = 1
DOUBLE_CLICK = 2
HOLD = 3


def send_button_event(device, tsn: int, button: int, press_type: int) -> None:
    """Receive a button event of the zigfred cluster, as a ZCL frame."""
    hdr = foundation.ZCLHeader.cluster(
        tsn=tsn,
        command_id=ZIGFRED_CLUSTER_COMMAND_BUTTON_EVENT,
        manufacturer=SIGLIS_MANUFACTURER_CODE,
        direction=foundation.Direction.Client_to_Server,
    )
    device.packet_received(
        t.ZigbeePacket(
            profile_id=260,
            cluster_id=ZIGFRED_CLUSTER_ID,
            src_ep=5,
            dst_ep=1,
            tsn=tsn,
            data=t.SerializableBytes(
                hdr.serialize() + t.uint32_t(button | press_type << 8).serialize()
            ),
        )
    )


@pytest.mark.parametrize("quirk", (ZigfredUno, ZigfredPlus))
async def test_zigfred_button_events(zigpy_device_from_quirk, quirk):
    """Test the button event entities of the zigfred front module buttons."""
    device = DEVICE_REGISTRY.resolve(zigpy_device_from_quirk(quirk, apply_quirk=False))
    assert isinstance(device, quirk)

    recorder = await ButtonEventRecorder.create(device)

    assert recorder.event_types() == {
        f"button_{number}": [
            "single_press",
            "multi_press",
            "long_press_start",
            "long_press_end",
        ]
        for number in (1, 2, 3, 4)
    }

    tsn = 10
    for button in range(4):
        for press_type in (CLICK, DOUBLE_CLICK, RELEASE, HOLD, HOLD, RELEASE):
            tsn += 1
            send_button_event(device, tsn, button, press_type)

        # A release without a hold is not classified, and a repeated hold is one
        # long press start
        assert recorder.pop() == [
            (f"button_{button + 1}", "single_press"),
            (f"button_{button + 1}", "multi_press", {"press_count": 2}),
            (f"button_{button + 1}", "long_press_start"),
            (f"button_{button + 1}", "long_press_end"),
        ]
