"""Tests for Legrand."""

from unittest import mock

import pytest
import zigpy.profiles.zha
import zigpy.types as t
from zigpy.zcl import AttributeUnsupportedEvent, ClusterType
from zigpy.zcl.clusters.general import (
    Basic,
    BinaryInput,
    Identify,
    Ota,
    PollControl,
    PowerConfiguration,
    Scenes,
)
from zigpy.zcl.foundation import ReadAttributeRecord, Status

from tests.common import ButtonEventRecorder
import zhaquirks
from zhaquirks.const import BatterySize
from zhaquirks.legrand import LEGRAND, MANUFACTURER_SPECIFIC_CLUSTER_ID

zhaquirks.setup()


@pytest.mark.parametrize(
    "voltage, bpr",
    (
        (32.00, 200),  # over the max
        (30.00, 200),  # max
        (29.0, 160),
        (28.0, 120),
        (27.50, 100),  # 50%
        (26.0, 40),
        (25.0, 0),  # min
        (24.0, 0),  # below min
    ),
)
async def test_legrand_battery(zigpy_device_from_quirk, voltage, bpr):
    """Test Legrand battery voltage to % battery left."""

    device = zigpy_device_from_quirk(zhaquirks.legrand.dimmer.RemoteDimmer)
    power_cluster = device.endpoints[1].power
    power_cluster.update_attribute(
        PowerConfiguration.AttributeDefs.battery_voltage.id, voltage
    )
    assert power_cluster["battery_percentage_remaining"] == bpr


async def test_power_config_unsupported_does_not_clear_cache(zigpy_device_from_quirk):
    """Test that reading unsupported battery_percentage_remaining doesn't clear the cached value."""

    device = zigpy_device_from_quirk(zhaquirks.legrand.dimmer.RemoteDimmer)
    power_cluster = device.endpoints[1].power

    # Simulate a voltage report that populates battery_percentage_remaining
    power_cluster.update_attribute(
        PowerConfiguration.AttributeDefs.battery_voltage.id, 28
    )
    assert power_cluster["battery_percentage_remaining"] == 120

    # Mock _read_attributes to return UNSUPPORTED_ATTRIBUTE for
    # battery_percentage_remaining, as a real device would during pairing
    bpr_attr_id = PowerConfiguration.AttributeDefs.battery_percentage_remaining.id
    unsupported_record = ReadAttributeRecord(
        attrid=t.uint16_t(bpr_attr_id),
        status=Status.UNSUPPORTED_ATTRIBUTE,
    )
    power_cluster._read_attributes = mock.AsyncMock(return_value=[[unsupported_record]])

    await power_cluster.read_attributes(
        [PowerConfiguration.AttributeDefs.battery_percentage_remaining.name]
    )

    # The cached value should be preserved
    assert power_cluster["battery_percentage_remaining"] == 120


async def test_power_config_other_unsupported_events_pass_through(
    zigpy_device_from_quirk,
):
    """Test that unsupported events for other attributes are not suppressed."""

    device = zigpy_device_from_quirk(zhaquirks.legrand.dimmer.RemoteDimmer)
    power_cluster = device.endpoints[1].power

    listener = mock.MagicMock()
    power_cluster.on_event(AttributeUnsupportedEvent.event_type, listener)

    # Mark a different attribute (battery_voltage) as unsupported
    power_cluster.add_unsupported_attribute(
        PowerConfiguration.AttributeDefs.battery_voltage.name
    )

    # The event should have reached the listener
    listener.assert_called_once()
    event = listener.call_args[0][0]
    assert event.attribute_id == PowerConfiguration.AttributeDefs.battery_voltage.id


async def test_legrand_wire_pilot_cluster_write_attrs(zigpy_device_from_v2_quirk):
    """Test Legrand cable outlet pilot_wire_mode attr writing."""

    device = zigpy_device_from_v2_quirk(f" {LEGRAND}", " Cable outlet")

    cable_cluster = device.endpoints[1].legrand_cable_outlet_cluster
    cable_cluster._write_attributes = mock.AsyncMock()
    cable_cluster._read_attributes = mock.AsyncMock()
    cable_cluster.set_pilot_wire_mode = mock.AsyncMock()

    # test writing read-only pilot_wire_mode attribute, should call set_pilot_wire_mode
    await cable_cluster.write_attributes({0x00: 0x02}, manufacturer=0x1021)

    cable_cluster.set_pilot_wire_mode.assert_awaited_with(
        0x02,
        manufacturer=0x1021,
    )
    # With an empty attrs dict, _write_attributes is not called in the new zigpy API
    assert len(cable_cluster._write_attributes.mock_calls) == 0


async def test_legrand_identify_command(zigpy_device_from_v2_quirk):
    """Test Legrand Identify cluster command handling."""

    device = zigpy_device_from_v2_quirk(f" {LEGRAND}", " Light switch with neutral")
    identify_cluster = device.endpoints[1].identify

    with mock.patch("zigpy.zcl.Cluster.request") as request:
        # Expected values for the mocked function calls
        IDENTIFY_TIME = 1234
        IDENTIFY_COMMAND = 0x00
        TRIGGER_EFFECT_COMMAND = 0x40
        EFFECT_ID = 0x00
        EFFECT_VARIANT = 0x00

        # Test the identify command
        await identify_cluster.identify(identify_time=IDENTIFY_TIME)

        # The identify command should produce two requests
        assert request.call_count == 2

        # The first call is for the trigger effect command
        assert request.call_args_list[0].args[1] == TRIGGER_EFFECT_COMMAND
        assert request.call_args_list[0].kwargs["effect_id"] == EFFECT_ID
        assert request.call_args_list[0].kwargs["effect_variant"] == EFFECT_VARIANT
        assert "identify_time" not in request.call_args_list[0].kwargs

        # The second call is for the identify command
        assert request.call_args_list[1].args[1] == IDENTIFY_COMMAND
        assert request.call_args_list[1].kwargs["identify_time"] == IDENTIFY_TIME
        assert "effect_id" not in request.call_args_list[1].kwargs
        assert "effect_variant" not in request.call_args_list[1].kwargs


MASTER_REMOTE_CLUSTERS = {
    1: {
        Basic.cluster_id: ClusterType.Server,
        PowerConfiguration.cluster_id: ClusterType.Server,
        Identify.cluster_id: ClusterType.Server,
        BinaryInput.cluster_id: ClusterType.Server,
        PollControl.cluster_id: ClusterType.Server,
        MANUFACTURER_SPECIFIC_CLUSTER_ID: ClusterType.Server,
        Scenes.cluster_id: ClusterType.Client,
        Ota.cluster_id: ClusterType.Client,
    }
}


def master_remote(zigpy_device_from_v2_quirk):
    """Return a quirked Legrand / BTicino wireless master remote."""
    device = zigpy_device_from_v2_quirk(
        f" {LEGRAND}",
        " Master remote SW Home / Away",
        cluster_ids=MASTER_REMOTE_CLUSTERS,
    )
    # The endpoint the remote reports, so ZHA discovers its cluster entities
    endpoint = device.endpoints[1]
    endpoint.profile_id = zigpy.profiles.zha.PROFILE_ID
    endpoint.device_type = zigpy.profiles.zha.DeviceType.REMOTE_CONTROL
    return device


def send_scenes_frame(device, data: bytes) -> None:
    """Receive a Scenes cluster frame from endpoint 1 of the remote."""
    device.packet_received(
        t.ZigbeePacket(
            src=t.AddrModeAddress(addr_mode=t.AddrMode.NWK, address=device.nwk),
            src_ep=1,
            dst=t.AddrModeAddress(addr_mode=t.AddrMode.NWK, address=0x0000),
            dst_ep=1,
            tsn=data[1],
            profile_id=zigpy.profiles.zha.PROFILE_ID,
            cluster_id=Scenes.cluster_id,
            data=t.SerializableBytes(data),
        )
    )


async def test_master_remote_battery(zigpy_device_from_v2_quirk):
    """Test the master remote battery: Legrand voltage conversion and a CR2032."""
    device = master_remote(zigpy_device_from_v2_quirk)
    power_cluster = device.endpoints[1].power

    assert power_cluster.get("battery_size") == BatterySize.CR2032
    assert power_cluster.get("battery_quantity") == 1

    power_cluster.update_attribute(
        PowerConfiguration.AttributeDefs.battery_voltage.id, 29
    )
    assert power_cluster["battery_percentage_remaining"] == 160


async def test_master_remote_button_events(zigpy_device_from_v2_quirk):
    """Test the master remote button event entities fire for real recall frames."""
    device = master_remote(zigpy_device_from_v2_quirk)
    recorder = await ButtonEventRecorder.create(device)

    assert recorder.event_types() == {
        "button_1": ["press_start"],
        "button_2": ["press_start"],
    }

    # The binary input has no use on this remote, so it gets no entity
    entity_clusters = {
        getattr(entity, "_cluster", None) and entity._cluster.cluster_id
        for entity in recorder.zha_device.platform_entities.values()
    }
    assert BinaryInput.cluster_id not in entity_clusters
    assert PowerConfiguration.cluster_id in entity_clusters

    # recall(group_id=0xFFF7, scene_id=1, transition_time=0), as sent by the remote
    send_scenes_frame(device, b"\x11\x06\x05\xf7\xff\x01\x00\x00")
    # recall(group_id=0xFFF6, scene_id=1, transition_time=0)
    send_scenes_frame(device, b"\x11\x07\x05\xf6\xff\x01\x00\x00")

    assert recorder.pop() == [
        ("button_1", "press_start"),
        ("button_2", "press_start"),
    ]
