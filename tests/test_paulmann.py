"""Tests for Paulmann quirks."""

import pytest
from zha.quirks import DEVICE_REGISTRY
from zigpy.zcl.clusters.general import LevelControl, OnOff

from tests.common import ButtonEventRecorder, send_command
import zhaquirks
import zhaquirks.paulmann.fourbtnremote

zhaquirks.setup()


@pytest.mark.parametrize("manufacturer", ("Paulmann LichtGmbH", "Paulmann Licht GmbH"))
def test_fourbtnremote_signature(assert_signature_matches_quirk, manufacturer):
    """Test PaulmannRemote4Btn signature is matched to its quirk."""
    signature = {
        "node_descriptor": "NodeDescriptor(logical_type=<LogicalType.EndDevice: 2>, complex_descriptor_available=0, user_descriptor_available=0, reserved=0, aps_flags=0, frequency_band=<FrequencyBand.Freq2400MHz: 8>, mac_capability_flags=<MACCapabilityFlags.AllocateAddress: 128>, manufacturer_code=4644, maximum_buffer_size=82, maximum_incoming_transfer_size=82, server_mask=11264, maximum_outgoing_transfer_size=82, descriptor_capability_field=<DescriptorCapability.NONE: 0>, *allocate_address=True, *is_alternate_pan_coordinator=False, *is_coordinator=False, *is_end_device=True, *is_full_function_device=False, *is_mains_powered=False, *is_receiver_on_when_idle=False, *is_router=False, *is_security_capable=False)",
        "endpoints": {
            "1": {
                "profile_id": 260,
                "device_type": "0x0001",
                "in_clusters": ["0x0000", "0x0001", "0x0003", "0x0b05", "0x1000"],
                "out_clusters": [
                    "0x0003",
                    "0x0004",
                    "0x0005",
                    "0x0006",
                    "0x0008",
                    "0x0019",
                    "0x0300",
                    "0x1000",
                ],
            },
            "2": {
                "profile_id": 260,
                "device_type": "0x0001",
                "in_clusters": ["0x0000", "0x0001", "0x0003", "0x0b05", "0x1000"],
                "out_clusters": [
                    "0x0003",
                    "0x0004",
                    "0x0005",
                    "0x0006",
                    "0x0008",
                    "0x0019",
                    "0x0300",
                    "0x1000",
                ],
            },
        },
        "manufacturer": manufacturer,
        "model": "501.34",
        "class": "paulmann.fourbtnremote.PaulmannRemote4Btn",
    }

    assert_signature_matches_quirk(
        zhaquirks.paulmann.fourbtnremote.PaulmannRemote4Btn, signature
    )


async def test_fourbtnremote_button_events(zigpy_device_from_quirk):
    """Test the button event entities of the Paulmann 4-button remote."""
    quirk = zhaquirks.paulmann.fourbtnremote.PaulmannRemote4Btn
    device = DEVICE_REGISTRY.resolve(zigpy_device_from_quirk(quirk, apply_quirk=False))
    assert isinstance(device, quirk)

    recorder = await ButtonEventRecorder.create(device)
    assert recorder.event_types() == {
        f"button_{number}": ["press_end", "long_press_start", "long_press_end"]
        for number in (1, 2, 3, 4)
    }

    for endpoint_id, (on_button, off_button) in (
        (1, ("button_1", "button_2")),
        (2, ("button_3", "button_4")),
    ):
        send_command(device, endpoint_id, OnOff.cluster_id, "on")
        send_command(device, endpoint_id, OnOff.cluster_id, "off")
        assert recorder.pop() == [(on_button, "press_end"), (off_button, "press_end")]

        # Both buttons of an endpoint stop with the same command
        for button, move_mode in ((on_button, 0), (off_button, 1)):
            send_command(
                device,
                endpoint_id,
                LevelControl.cluster_id,
                "move_with_on_off",
                move_mode,
                50,
            )
            send_command(
                device, endpoint_id, LevelControl.cluster_id, "stop_with_on_off"
            )
            assert recorder.pop() == [
                (button, "long_press_start"),
                (button, "long_press_end"),
            ]

        # A stop without a hold fires nothing
        send_command(device, endpoint_id, LevelControl.cluster_id, "stop_with_on_off")
        assert recorder.pop() == []

    # A move at another rate is no trigger of the remote
    send_command(device, 1, LevelControl.cluster_id, "move_with_on_off", 0, 20)
    send_command(device, 1, OnOff.cluster_id, "toggle")
    assert recorder.pop() == []
