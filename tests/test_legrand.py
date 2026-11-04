"""Tests for Legrand."""

from unittest import mock

import pytest
import zigpy.types as t
from zigpy.zcl import AttributeUnsupportedEvent, ClusterType
from zigpy.zcl.clusters.general import OnOff, PowerConfiguration
from zigpy.zcl.foundation import ReadAttributeRecord, Status

import zhaquirks
from zhaquirks.const import BUTTON_1, BUTTON_2, COMMAND, ENDPOINT_ID, TURN_OFF, TURN_ON
from zhaquirks.legrand import LEGRAND

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


@pytest.mark.parametrize(
    ("endpoint_id", "frame", "command_name"),
    [
        (2, b"\x11\x1b\x00", "off"),
        (2, b"\x11\x1c\x01", "on"),
        (1, b"\x11\x1b\x00", "off"),
        (1, b"\x11\x1c\x01", "on"),
    ],
)
async def test_legrand_double_gangs_remote_switch_buttons(
    zigpy_device_from_v2_quirk, endpoint_id, frame, command_name
):
    """Test Double gangs remote switch only emits On/Off commands per endpoint."""

    device = zigpy_device_from_v2_quirk(
        f" {LEGRAND}",
        " Double gangs remote switch",
        cluster_ids={
            1: {OnOff.cluster_id: ClusterType.Client},
            2: {OnOff.cluster_id: ClusterType.Client},
        },
    )
    cluster = device.endpoints[endpoint_id].out_clusters[OnOff.cluster_id]
    listener = mock.MagicMock()
    cluster.add_listener(listener)

    device.packet_received(
        t.ZigbeePacket(
            profile_id=260,
            cluster_id=OnOff.cluster_id,
            src_ep=endpoint_id,
            dst_ep=endpoint_id,
            data=t.SerializableBytes(frame),
        )
    )

    assert listener.cluster_command.call_count == 1
    command_id = listener.cluster_command.call_args.args[1]
    assert getattr(OnOff.ServerCommandDefs, command_name).id == command_id

    triggers = device.device_automation_triggers
    assert set(triggers) == {
        (TURN_ON, BUTTON_1),
        (TURN_OFF, BUTTON_1),
        (TURN_ON, BUTTON_2),
        (TURN_OFF, BUTTON_2),
    }
    button = BUTTON_1 if endpoint_id == 1 else BUTTON_2
    trigger = TURN_ON if command_name == "on" else TURN_OFF
    assert triggers[(trigger, button)] == {
        COMMAND: command_name,
        ENDPOINT_ID: endpoint_id,
    }
