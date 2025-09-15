"""Tests for AduroSmart Eria Quirks."""

import pytest

import zhaquirks
from zhaquirks.aduro.adurolightcsc import AdurolightCSCRemote, AdurolightFcccCluster

zhaquirks.setup()


def test_adurolightcsc_signature(assert_signature_matches_quirk):
    """Signature should match the trimmed ZLL shape used for matching."""
    signature = {
        "node_descriptor": "NodeDescriptor(logical_type=<LogicalType.EndDevice: 2>, complex_descriptor_available=0, user_descriptor_available=0, reserved=0, aps_flags=0, frequency_band=<FrequencyBand.Freq2400MHz: 8>, mac_capability_flags=<MACCapabilityFlags.AllocateAddress: 128>, manufacturer_code=4653, maximum_buffer_size=127, maximum_incoming_transfer_size=100, server_mask=0, maximum_outgoing_transfer_size=100, descriptor_capability_field=<DescriptorCapability.NONE: 0>, *allocate_address=True, *is_alternate_pan_coordinator=False, *is_coordinator=False, *is_end_device=True, *is_full_function_device=False, *is_mains_powered=False, *is_receiver_on_when_idle=False, *is_router=False, *is_security_capable=False)",
        "endpoints": {
            "1": {
                "profile_id": 49246,  # 0xC05E (ZLL)
                "device_type": "0x0810",
                "in_clusters": [
                    "0x0000",
                    "0x0001",
                    "0x0003",
                    "0x0004",
                    "0x0005",
                    "0x1000",
                    "0xfccc",
                ],
                "out_clusters": [
                    "0x0000",
                    "0x0003",
                    "0x0004",
                    "0x0005",
                    "0x1000",
                    "0xfccc",
                ],
            },
            "2": {
                "profile_id": 49246,
                "device_type": "0x03f2",
                "in_clusters": ["0x1000"],
                "out_clusters": ["0x1000"],
            },
        },
        "manufacturer": "AduroSmart Eria",
        "model": "ADUROLIGHT_CSC",
        "class": "zhaquirks.aduro.adurolightcsc.AdurolightCSCRemote",
    }
    assert_signature_matches_quirk(AdurolightCSCRemote, signature)


@pytest.mark.parametrize(
    "args,expected_event",
    [
        ([0, 0], "button_1_short_press"),
        ([0, 1], "button_2_short_press"),
        ([0, 2], "button_3_short_press"),
        ([0, 3], "button_4_short_press"),
        ([1, 0], "button_1_long_press"),
        ([1, 1], "button_2_long_press"),
        ([1, 2], "button_3_long_press"),
        ([1, 3], "button_4_long_press"),
    ],
)
def test_handle_all_buttons(zigpy_device_from_quirk, args, expected_event):
    """Test handling of all button presses."""
    device = zigpy_device_from_quirk(AdurolightCSCRemote)
    cluster = device.endpoints[1].in_clusters[AdurolightFcccCluster.cluster_id]
    events = []
    cluster.listener_event = lambda *a, **k: events.append((a, k))

    hdr = type("ZCLHeader", (), {"command_id": 0, "tsn": 1})()
    result = cluster.handle_cluster_request(hdr, args)

    assert result is True
    assert events[0][0][1] == expected_event


def test_handle_invalid_command(zigpy_device_from_quirk):
    """Test handling of an invalid command."""
    device = zigpy_device_from_quirk(AdurolightCSCRemote)
    cluster = device.endpoints[1].in_clusters[AdurolightFcccCluster.cluster_id]

    hdr = type("ZCLHeader", (), {"command_id": 1, "tsn": 2})()
    args = [0, 0]
    result = cluster.handle_cluster_request(hdr, args)

    assert result is False


def test_handle_unknown_button(zigpy_device_from_quirk, caplog):
    """Test handling of an unknown button press."""
    device = zigpy_device_from_quirk(AdurolightCSCRemote)
    cluster = device.endpoints[1].in_clusters[AdurolightFcccCluster.cluster_id]

    hdr = type("ZCLHeader", (), {"command_id": 0, "tsn": 3})()
    args = [9, 9]
    with caplog.at_level("DEBUG"):
        result = cluster.handle_cluster_request(hdr, args)

    assert result is False
    assert "[FCCC] Unknown button key:" in caplog.text


def test_debounce_logic(zigpy_device_from_quirk, monkeypatch):
    """Test debounce logic for button presses."""
    device = zigpy_device_from_quirk(AdurolightCSCRemote)
    cluster = device.endpoints[1].in_clusters[AdurolightFcccCluster.cluster_id]
    events = []
    cluster.listener_event = lambda *a, **k: events.append((a, k))

    fake_time = [1000.0]
    monkeypatch.setattr(
        "zhaquirks.aduro.adurolightcsc.time.monotonic", lambda: fake_time[0]
    )

    hdr = type("ZCLHeader", (), {"command_id": 0, "tsn": 4})()
    args = [0, 0]

    result1 = cluster.handle_cluster_request(hdr, args)
    fake_time[0] += 0.5
    result2 = cluster.handle_cluster_request(hdr, args)
    fake_time[0] += 2.0
    result3 = cluster.handle_cluster_request(hdr, args)

    assert result1 is True
    assert result2 is True
    assert result3 is True
    assert len(events) == 2
    assert events[0][0][1] == "button_1_short_press"
    assert events[1][0][1] == "button_1_short_press"
