"""Tests for Tuya garage door quirks."""

from unittest import mock

import pytest
from zigpy.zcl import foundation
from zigpy.zcl.clusters.security import IasZone

from tests.common import ClusterListener
import zhaquirks
from zhaquirks.tuya.mcu import TuyaMCUCluster
from zhaquirks.tuya.ts0601_garage import ContactSwitchCluster, TuyaMoesGarageSwitch

zhaquirks.setup()


def test_tuya_moes_garage_signature(assert_signature_matches_quirk):
    """Test Tuya Moes Garage Door Opener signature is matched to its quirk."""

    signature = {
        "node_descriptor": "NodeDescriptor(logical_type=<LogicalType.Router: 1>, complex_descriptor_available=0, user_descriptor_available=0, reserved=0, aps_flags=0, frequency_band=<FrequencyBand.Freq2400MHz: 8>, mac_capability_flags=<MACCapabilityFlags.AllocateAddress|RxOnWhenIdle|MainsPowered|FullFunctionDevice: 142>, manufacturer_code=4417, maximum_buffer_size=66, maximum_incoming_transfer_size=66, server_mask=11264, maximum_outgoing_transfer_size=66, descriptor_capability_field=<DescriptorCapability.NONE: 0>, *allocate_address=True, *is_alternate_pan_coordinator=False, *is_coordinator=False, *is_end_device=False, *is_full_function_device=True, *is_mains_powered=True, *is_receiver_on_when_idle=True, *is_router=True, *is_security_capable=False)",
        "endpoints": {
            "1": {
                "profile_id": 260,
                "device_type": "0x0051",
                "in_clusters": ["0x0000", "0x0004", "0x0005", "0xef00"],
                "out_clusters": ["0x000a", "0x0019"],
            },
            "242": {
                "profile_id": 41440,
                "device_type": "0x0061",
                "in_clusters": [],
                "out_clusters": ["0x0021"],
            },
        },
        "manufacturer": "_TZE204_jktmrpoj",
        "model": "TS0601",
        "class": "tuya.ts0601_garage.TuyaMoesGarageSwitch",
    }

    assert_signature_matches_quirk(TuyaMoesGarageSwitch, signature)


async def test_moes_garage_switch_on_off(zigpy_device_from_quirk):
    """Test Tuya Moes garage door opener switch on/off control."""

    device = zigpy_device_from_quirk(TuyaMoesGarageSwitch)
    tuya_cluster = device.endpoints[1].in_clusters[TuyaMCUCluster.cluster_id]
    switch_cluster = device.endpoints[1].on_off
    tuya_listener = ClusterListener(tuya_cluster)

    # Test initial state
    assert len(tuya_listener.cluster_commands) == 0
    assert len(tuya_listener.attribute_updates) == 0

    # Test switch on command
    with mock.patch.object(
        tuya_cluster.endpoint, "request", return_value=foundation.Status.SUCCESS
    ):
        rsp = await switch_cluster.command(0x0001)
        assert rsp.status == foundation.Status.SUCCESS

    # Test switch off command
    with mock.patch.object(
        tuya_cluster.endpoint, "request", return_value=foundation.Status.SUCCESS
    ):
        rsp = await switch_cluster.command(0x0000)
        assert rsp.status == foundation.Status.SUCCESS


@pytest.mark.parametrize(
    ("data", "expected_zone_status"),
    [
        (
            # DP3 = True (door open/alarm)
            b"\x09\x00\x02\x00\x00\x03\x01\x00\x01\x01",
            IasZone.ZoneStatus.Alarm_1,
        ),
        (
            # DP3 = False (door closed)
            b"\x09\x00\x02\x00\x00\x03\x01\x00\x01\x00",
            0x0000,
        ),
    ],
)
async def test_moes_garage_door_contact_sensor(
    zigpy_device_from_quirk, data, expected_zone_status
):
    """Test Tuya Moes garage door contact sensor reports."""

    device = zigpy_device_from_quirk(TuyaMoesGarageSwitch)
    tuya_cluster = device.endpoints[1].in_clusters[TuyaMCUCluster.cluster_id]
    contact_cluster = device.endpoints[2].in_clusters[ContactSwitchCluster.cluster_id]

    contact_listener = ClusterListener(contact_cluster)

    # Deserialize and handle the message
    hdr, payload = tuya_cluster.deserialize(data)
    tuya_cluster.handle_message(hdr, payload)

    # Verify the contact sensor received the update
    assert len(contact_listener.attribute_updates) == 1
    assert (
        contact_listener.attribute_updates[0][0]
        == ContactSwitchCluster.AttributeDefs.zone_status.id
    )
    assert contact_listener.attribute_updates[0][1] == expected_zone_status


@pytest.mark.parametrize(
    ("dp_id", "dp_data", "attr_name", "expected_value"),
    [
        (2, b"\x00\x00\x00\x3c", "countdown", 60),  # DP2: countdown = 60 seconds
        (4, b"\x00\x00\x00\x0a", "run_time", 10),  # DP4: run_time = 10
        (5, b"\x00\x00\x00\x78", "open_alarm_time", 120),  # DP5: alarm time = 120
        (12, b"\x02", "status", 0x02),  # DP12: status = 2
    ],
)
async def test_moes_garage_attributes(
    zigpy_device_from_quirk, dp_id, dp_data, attr_name, expected_value
):
    """Test Tuya Moes garage door attribute updates."""

    device = zigpy_device_from_quirk(TuyaMoesGarageSwitch)
    tuya_cluster = device.endpoints[1].in_clusters[TuyaMCUCluster.cluster_id]
    tuya_listener = ClusterListener(tuya_cluster)

    # Build the Tuya message with the DP
    # Format: header + DP ID + type + length + data
    if isinstance(dp_data, bytes) and len(dp_data) == 1:
        # ENUM type (0x04)
        data = b"\x09\x00\x02\x00\x00" + bytes([dp_id]) + b"\x04\x00\x01" + dp_data
    else:
        # VALUE type (0x02)
        data = b"\x09\x00\x02\x00\x00" + bytes([dp_id]) + b"\x02\x00\x04" + dp_data

    # Deserialize and handle the message
    hdr, payload = tuya_cluster.deserialize(data)
    tuya_cluster.handle_message(hdr, payload)

    # Verify the attribute was updated
    assert len(tuya_listener.attribute_updates) >= 1
    attr_id = tuya_cluster.attributes_by_name[attr_name].id
    # Find the update for this attribute
    updates = [u for u in tuya_listener.attribute_updates if u[0] == attr_id]
    assert len(updates) == 1
    assert updates[0][1] == expected_value
