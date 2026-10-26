"""Tests for Samjin quirks."""

import pytest
from zha.quirks import DEVICE_REGISTRY
from zigpy.zcl import ClusterType
from zigpy.zcl.clusters.security import IasZone

from tests.common import ButtonEventRecorder, send_command
import zhaquirks
from zhaquirks.samjin.button import SamjinButton, SamjinButton2

zhaquirks.setup()


@pytest.mark.parametrize("quirk", (SamjinButton, SamjinButton2))
async def test_button_events(zigpy_device_from_quirk, quirk):
    """Test the button event entity of the Samjin button."""
    device = DEVICE_REGISTRY.resolve(zigpy_device_from_quirk(quirk, apply_quirk=False))
    assert isinstance(device, quirk)

    recorder = await ButtonEventRecorder.create(device)
    assert recorder.event_types() == {
        "button": ["single_press", "multi_press", "long_press_start"]
    }

    # The two lowest bits of the zone status tell the press type
    for zone_status in (0x0001, 0x0002, 0x0003):
        send_command(
            device,
            1,
            IasZone.cluster_id,
            "status_change_notification",
            zone_status,
            0,
            0,
            0,
            cluster_type=ClusterType.Server,
        )

    assert recorder.pop() == [
        ("button", "single_press"),
        ("button", "multi_press", {"press_count": 2}),
        ("button", "long_press_start"),
    ]
