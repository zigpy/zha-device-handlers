"""Tests for YOKIS quirks."""

import pytest
from zigpy.profiles import zha
from zigpy.zcl import ClusterType
from zigpy.zcl.clusters.general import LevelControl, OnOff

from tests.common import ButtonEventRecorder, send_command
import zhaquirks

zhaquirks.setup()


async def test_yokis_one_button_remote_button_events(zigpy_device_from_v2_quirk):
    """Test the button event entity of the YOKIS one button remotes."""
    device = zigpy_device_from_v2_quirk(
        "YOKIS",
        "TLC1-UP",
        cluster_ids={1: {OnOff.cluster_id: ClusterType.Client}},
    )
    device.endpoints[1].profile_id = zha.PROFILE_ID
    device.endpoints[1].device_type = zha.DeviceType.ON_OFF_SWITCH

    recorder = await ButtonEventRecorder.create(device)
    assert recorder.event_types() == {"button": ["single_press"]}

    send_command(device, 1, OnOff.cluster_id, "toggle")
    send_command(device, 1, OnOff.cluster_id, "on")
    assert recorder.pop() == [("button", "single_press")]


@pytest.mark.parametrize(
    "model, buttons",
    [
        ("TLC2-UP", 2),
        ("E2BP-UP", 2),
        ("TLC4-UP", 4),
        ("GALET4-UP", 4),
        ("TLC8-UP", 8),
        ("MONITOR-UP", 8),
    ],
)
async def test_yokis_remote_button_events(zigpy_device_from_v2_quirk, model, buttons):
    """Test the button event entities of the YOKIS multi button remotes."""
    endpoint_ids = range(1, buttons + 1)
    device = zigpy_device_from_v2_quirk(
        "YOKIS",
        model,
        cluster_ids={
            endpoint_id: {
                OnOff.cluster_id: ClusterType.Client,
                LevelControl.cluster_id: ClusterType.Client,
            }
            for endpoint_id in endpoint_ids
        },
    )
    for endpoint_id in endpoint_ids:
        device.endpoints[endpoint_id].profile_id = zha.PROFILE_ID
        device.endpoints[endpoint_id].device_type = zha.DeviceType.ON_OFF_SWITCH

    recorder = await ButtonEventRecorder.create(device)
    assert recorder.event_types() == {
        f"button_{number}": ["single_press"] for number in endpoint_ids
    }

    for endpoint_id in endpoint_ids:
        send_command(device, endpoint_id, OnOff.cluster_id, "toggle")
        send_command(device, endpoint_id, OnOff.cluster_id, "off")
        send_command(device, endpoint_id, LevelControl.cluster_id, "stop")

    assert recorder.pop() == [
        (f"button_{number}", "single_press") for number in endpoint_ids
    ]
    assert all(
        recorder.entities[f"button_{number}"].endpoint.id == number
        for number in endpoint_ids
    )
