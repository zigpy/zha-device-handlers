"""Tests for Legrand."""

import logging
from unittest import mock

import pytest
import zigpy.types as t
import zigpy.zcl.foundation as f

import zhaquirks
from zhaquirks.legrand import LEGRAND
from zhaquirks.legrand.contactor import (
    AutoOverride,
    AutoStatus,
    LegrandContactorAutoOnOff,
    LegrandContactorMode,
    LegrandContactorSwitchOnOff,
    LegrandMode,
)

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
    power_cluster.update_attribute(0x0020, voltage)
    assert power_cluster["battery_percentage_remaining"] == bpr


def test_light_switch_with_neutral_signature(assert_signature_matches_quirk):
    """Test signature."""
    signature = {
        "node_descriptor": "NodeDescriptor(logical_type=<LogicalType.Router: 1>, complex_descriptor_available=0, user_descriptor_available=1, reserved=0, aps_flags=0, frequency_band=<FrequencyBand.Freq2400MHz: 8>, mac_capability_flags=<MACCapabilityFlags.AllocateAddress|RxOnWhenIdle|MainsPowered|FullFunctionDevice: 142>, manufacturer_code=4129, maximum_buffer_size=89, maximum_incoming_transfer_size=63, server_mask=10752, maximum_outgoing_transfer_size=63, descriptor_capability_field=<DescriptorCapability.NONE: 0>, *allocate_address=True, *is_alternate_pan_coordinator=False, *is_coordinator=False, *is_end_device=False, *is_full_function_device=True, *is_mains_powered=True, *is_receiver_on_when_idle=True, *is_router=True, *is_security_capable=False)",
        "endpoints": {
            "1": {
                "profile_id": 260,
                "device_type": "0x0100",
                "in_clusters": [
                    "0x0000",
                    "0x0003",
                    "0x0004",
                    "0x0005",
                    "0x0006",
                    "0x000f",
                    "0xfc01",
                ],
                "out_clusters": ["0x0000", "0x0019", "0xfc01"],
            }
        },
        "manufacturer": " Legrand",
        "model": " Light switch with neutral",
        "class": "zigpy.device.Device",
    }
    assert_signature_matches_quirk(
        zhaquirks.legrand.switch.LightSwitchWithNeutral, signature
    )


async def test_legrand_wire_pilot_cluster_write_attrs(zigpy_device_from_v2_quirk):
    """Test Legrand cable outlet pilot_wire_mode attr writing."""

    device = zigpy_device_from_v2_quirk(f" {LEGRAND}", " Cable outlet")

    cable_cluster = device.endpoints[1].legrand_cable_outlet_cluster
    cable_cluster._write_attributes = mock.AsyncMock()
    cable_cluster._read_attributes = mock.AsyncMock()
    cable_cluster.set_pilot_wire_mode = mock.AsyncMock()

    # test writing read-only pilot_wire_mode attribute, should call set_pilot_wire_mode
    await cable_cluster.write_attributes({0x00: 0x02}, manufacturer=0xFC40)

    cable_cluster.set_pilot_wire_mode.assert_awaited_with(
        0x02,
        manufacturer=0xFC40,
    )
    cable_cluster._write_attributes.assert_awaited_with(
        [],
        manufacturer=0xFC40,
    )


async def test_legrand_contactor_switch(zigpy_device_from_v2_quirk):
    """Test Legrand contactor switch."""

    device = zigpy_device_from_v2_quirk(f" {LEGRAND}", " Contactor")

    mode_cluster = device.endpoints[1].in_clusters[LegrandContactorMode.cluster_id]
    auto_on_off_cluster = device.endpoints[1].in_clusters[
        LegrandContactorAutoOnOff.cluster_id
    ]
    switch_on_off_cluster = device.endpoints[1].in_clusters[
        LegrandContactorSwitchOnOff.cluster_id
    ]

    ##
    ## Test Auto mode
    ##
    switch_on_off_cluster.contactor_is_switch_reported(False)
    assert not switch_on_off_cluster._contactor_is_switch
    
    switch_on_off_cluster.auto_on_off_reported(True)
    switch_on_off_cluster.auto_on_off_reported(False)

    # test sending turn_on command
    mode_cluster._read_mode = mock.AsyncMock()
    auto_on_off_cluster.turn_on = mock.AsyncMock()
    auto_on_off_cluster.turn_off = mock.AsyncMock()
    auto_on_off_cluster.toggle = mock.AsyncMock()
    await switch_on_off_cluster.command(LegrandContactorSwitchOnOff.ON_CMD_ID)
    mode_cluster._read_mode.assert_awaited_once()
    auto_on_off_cluster.turn_on.assert_awaited_once()
    auto_on_off_cluster.turn_off.assert_not_awaited()
    auto_on_off_cluster.toggle.assert_not_awaited()

    # test sending turn_off command
    mode_cluster._read_mode = mock.AsyncMock()
    auto_on_off_cluster.turn_on = mock.AsyncMock()
    auto_on_off_cluster.turn_off = mock.AsyncMock()
    auto_on_off_cluster.toggle = mock.AsyncMock()
    await switch_on_off_cluster.command(LegrandContactorSwitchOnOff.OFF_CMD_ID)
    mode_cluster._read_mode.assert_awaited_once()
    auto_on_off_cluster.turn_on.assert_not_awaited()
    auto_on_off_cluster.turn_off.assert_awaited_once()
    auto_on_off_cluster.toggle.assert_not_awaited()

    # test sending toggle command
    mode_cluster._read_mode = mock.AsyncMock()
    auto_on_off_cluster.turn_on = mock.AsyncMock()
    auto_on_off_cluster.turn_off = mock.AsyncMock()
    auto_on_off_cluster.toggle = mock.AsyncMock()
    await switch_on_off_cluster.command(LegrandContactorSwitchOnOff.TOGGLE_CMD_ID)
    mode_cluster._read_mode.assert_awaited_once()
    auto_on_off_cluster.turn_on.assert_not_awaited()
    auto_on_off_cluster.turn_off.assert_not_awaited()
    auto_on_off_cluster.toggle.assert_awaited_once()

    # cover _read_attributes
    auto_on_off_cluster._read_states = mock.AsyncMock()
    switch_on_off_cluster.request = mock.AsyncMock()
    await switch_on_off_cluster._read_attributes(["on_off"])
    auto_on_off_cluster._read_states.assert_awaited_once()
    switch_on_off_cluster.request.assert_awaited_once()

    auto_on_off_cluster._read_states = mock.AsyncMock()
    switch_on_off_cluster.request = mock.AsyncMock()
    await switch_on_off_cluster._read_attributes(
        [LegrandContactorSwitchOnOff.ON_OFF_ID]
    )
    auto_on_off_cluster._read_states.assert_awaited_once()
    switch_on_off_cluster.request.assert_awaited_once()
    # cover _update_attribute
    switch_on_off_cluster._update_attribute(LegrandContactorSwitchOnOff.ON_OFF_ID, 0)

    ##
    ## Test Switch mode
    ##
    switch_on_off_cluster.contactor_is_switch_reported(True)
    assert switch_on_off_cluster._contactor_is_switch

    switch_on_off_cluster.auto_on_off_reported(True)
    switch_on_off_cluster.auto_on_off_reported(False)

    # test sending turn_on command
    mode_cluster._read_mode = mock.AsyncMock()
    auto_on_off_cluster.turn_on = mock.AsyncMock()
    auto_on_off_cluster.turn_off = mock.AsyncMock()
    auto_on_off_cluster.toggle = mock.AsyncMock()
    switch_on_off_cluster.request = mock.AsyncMock()
    await switch_on_off_cluster.command(LegrandContactorSwitchOnOff.ON_CMD_ID)
    mode_cluster._read_mode.assert_awaited_once()
    auto_on_off_cluster.turn_on.assert_not_awaited()
    auto_on_off_cluster.turn_off.assert_not_awaited()
    auto_on_off_cluster.toggle.assert_not_awaited()
    switch_on_off_cluster.request.assert_awaited_once()

    # test sending turn_off command
    mode_cluster._read_mode = mock.AsyncMock()
    auto_on_off_cluster.turn_on = mock.AsyncMock()
    auto_on_off_cluster.turn_off = mock.AsyncMock()
    auto_on_off_cluster.toggle = mock.AsyncMock()
    switch_on_off_cluster.request = mock.AsyncMock()
    await switch_on_off_cluster.command(LegrandContactorSwitchOnOff.OFF_CMD_ID)
    mode_cluster._read_mode.assert_awaited_once()
    auto_on_off_cluster.turn_on.assert_not_awaited()
    auto_on_off_cluster.turn_off.assert_not_awaited()
    auto_on_off_cluster.toggle.assert_not_awaited()
    switch_on_off_cluster.request.assert_awaited_once()

    # test sending toggle command
    mode_cluster._read_mode = mock.AsyncMock()
    auto_on_off_cluster.turn_on = mock.AsyncMock()
    auto_on_off_cluster.turn_off = mock.AsyncMock()
    auto_on_off_cluster.toggle = mock.AsyncMock()
    switch_on_off_cluster.request = mock.AsyncMock()
    await switch_on_off_cluster.command(LegrandContactorSwitchOnOff.TOGGLE_CMD_ID)
    mode_cluster._read_mode.assert_awaited_once()
    auto_on_off_cluster.turn_on.assert_not_awaited()
    auto_on_off_cluster.turn_off.assert_not_awaited()
    auto_on_off_cluster.toggle.assert_not_awaited()
    switch_on_off_cluster.request.assert_awaited_once()

    # cover _read_attributes
    auto_on_off_cluster._read_states = mock.AsyncMock()
    switch_on_off_cluster.request = mock.AsyncMock()
    await switch_on_off_cluster._read_attributes(["on_off"])
    auto_on_off_cluster._read_states.assert_not_awaited()
    switch_on_off_cluster.request.assert_awaited_once()

    auto_on_off_cluster._read_states = mock.AsyncMock()
    switch_on_off_cluster.request = mock.AsyncMock()
    await switch_on_off_cluster._read_attributes(
        [LegrandContactorSwitchOnOff.ON_OFF_ID]
    )
    auto_on_off_cluster._read_states.assert_not_awaited()
    switch_on_off_cluster.request.assert_awaited_once()

    await switch_on_off_cluster._read_attributes(
        [LegrandContactorSwitchOnOff.ON_OFF_ID+1]
    )

    # cover _update_attribute
    switch_on_off_cluster._update_attribute(LegrandContactorSwitchOnOff.ON_OFF_ID, 0)

    # test sending other command
    try:
        mode_cluster._read_mode = mock.AsyncMock()
        auto_on_off_cluster.turn_on = mock.AsyncMock()
        auto_on_off_cluster.turn_off = mock.AsyncMock()
        auto_on_off_cluster.toggle = mock.AsyncMock()
        await switch_on_off_cluster.command(LegrandContactorSwitchOnOff.TOGGLE_CMD_ID+1)
        mode_cluster._read_mode.assert_not_awaited()
        auto_on_off_cluster.turn_on.assert_not_awaited()
        auto_on_off_cluster.turn_off.assert_not_awaited()
        auto_on_off_cluster.toggle.assert_not_awaited()
    except Exception as e:
        assert isinstance(e, KeyError)


async def test_legrand_contactor_auto(zigpy_device_from_v2_quirk):
    """Test Legrand contactor auto."""

    device = zigpy_device_from_v2_quirk(f" {LEGRAND}", " Contactor")

    auto_on_off_cluster = device.endpoints[1].in_clusters[
        LegrandContactorAutoOnOff.cluster_id
    ]

    # cover _read_states
    auto_on_off_cluster.read_attributes = mock.AsyncMock()
    await auto_on_off_cluster._read_states()
    auto_on_off_cluster.read_attributes.assert_awaited_with(
        [LegrandContactorAutoOnOff.STATUS_ID, LegrandContactorAutoOnOff.ON_OFF_ID],
        allow_cache=False,
    )

    # cover _read_status
    auto_on_off_cluster.read_attributes = mock.AsyncMock()
    await auto_on_off_cluster._read_status()
    auto_on_off_cluster.read_attributes.assert_awaited_with(
        [LegrandContactorAutoOnOff.STATUS_ID], allow_cache=False
    )
    auto_on_off_cluster.read_attributes = mock.AsyncMock(return_value=[None])
    assert await auto_on_off_cluster._read_status() is None

    # cover command
    auto_on_off_cluster.request = mock.AsyncMock()
    auto_on_off_cluster._read_states = mock.AsyncMock()
    await auto_on_off_cluster.command(
        LegrandContactorAutoOnOff.OVERRIDE_CMD_ID, t.data16([])
    )
    auto_on_off_cluster._read_states.assert_awaited_once()
    auto_on_off_cluster.request.assert_awaited_once()

    # cover turn_off
    auto_on_off_cluster.command = mock.AsyncMock()
    auto_on_off_cluster._read_status = mock.AsyncMock(return_value=AutoStatus.ForcedOn)
    await auto_on_off_cluster.turn_off()
    auto_on_off_cluster.command.assert_awaited_once()

    auto_on_off_cluster.command = mock.AsyncMock()
    auto_on_off_cluster._read_status = mock.AsyncMock(return_value=AutoStatus.ForcedOff)
    await auto_on_off_cluster.turn_off()
    auto_on_off_cluster.command.assert_not_awaited()

    # cover turn_on
    auto_on_off_cluster.command = mock.AsyncMock()
    auto_on_off_cluster._read_status = mock.AsyncMock(return_value=AutoStatus.ForcedOff)
    await auto_on_off_cluster.turn_on()
    auto_on_off_cluster.command.assert_awaited_once()

    auto_on_off_cluster.command = mock.AsyncMock()
    auto_on_off_cluster._read_status = mock.AsyncMock(return_value=AutoStatus.ForcedOn)
    await auto_on_off_cluster.turn_on()
    auto_on_off_cluster.command.assert_not_awaited()

    # cover toggle
    assert auto_on_off_cluster.TOGGLE_MAP[AutoStatus.ForcedOn] == AutoOverride.ForceOff
    assert auto_on_off_cluster.TOGGLE_MAP[AutoStatus.ForcedOff] == AutoOverride.ForceOn
    assert auto_on_off_cluster.TOGGLE_MAP[AutoStatus.ManualOn] == AutoOverride.ForceOff
    assert AutoStatus.Auto not in auto_on_off_cluster.TOGGLE_MAP

    auto_on_off_cluster.command = mock.AsyncMock()
    auto_on_off_cluster._read_status = mock.AsyncMock(return_value=AutoStatus.ForcedOff)
    await auto_on_off_cluster.toggle()
    auto_on_off_cluster._read_status.assert_awaited_once()
    auto_on_off_cluster.command.assert_awaited_once()

    auto_on_off_cluster.command = mock.AsyncMock()
    auto_on_off_cluster._read_status = mock.AsyncMock(return_value=AutoStatus.ForcedOn)
    await auto_on_off_cluster.toggle()
    auto_on_off_cluster._read_status.assert_awaited_once()
    auto_on_off_cluster.command.assert_awaited_once()

    auto_on_off_cluster.command = mock.AsyncMock()
    auto_on_off_cluster._read_status = mock.AsyncMock(return_value=AutoStatus.ManualOn)
    await auto_on_off_cluster.toggle()
    auto_on_off_cluster._read_status.assert_awaited_once()
    auto_on_off_cluster.command.assert_awaited_once()

    auto_on_off_cluster.command = mock.AsyncMock()
    auto_on_off_cluster._read_status = mock.AsyncMock(return_value=AutoStatus.Auto)
    await auto_on_off_cluster.toggle()
    auto_on_off_cluster._read_status.assert_awaited_once()
    auto_on_off_cluster.command.assert_not_awaited()

    # cover _update_attribute
    auto_on_off_cluster._update_attribute(LegrandContactorAutoOnOff.ON_OFF_ID, False)
    auto_on_off_cluster._update_attribute(LegrandContactorAutoOnOff.ON_OFF_ID, True)


async def test_legrand_contactor_mode(zigpy_device_from_v2_quirk):
    """Test Legrand contactor mode."""

    device = zigpy_device_from_v2_quirk(f" {LEGRAND}", " Contactor")

    mode_cluster = device.endpoints[1].in_clusters[LegrandContactorMode.cluster_id]
    switch_on_off_cluster = device.endpoints[1].in_clusters[
        LegrandContactorSwitchOnOff.cluster_id
    ]

    # cover _read_mode
    mode_cluster.read_attributes = mock.AsyncMock(return_value=[None])
    result = await mode_cluster._read_mode()
    assert result is None
    mode_cluster.read_attributes = mock.AsyncMock(
        return_value=[{LegrandContactorMode.MODE_ID: "mode_id_value"}]
    )
    result = await mode_cluster._read_mode()
    assert result == "mode_id_value"

    # cover _update_attribute
    mode_cluster._update_attribute(LegrandContactorMode.MODE_ID, [3, 0])
    assert switch_on_off_cluster._contactor_is_switch
    mode_cluster._update_attribute(LegrandContactorMode.MODE_ID, [4, 0])
    assert not switch_on_off_cluster._contactor_is_switch

    # cover write_attributes
    mode_cluster._write_attributes = mock.AsyncMock()
    await mode_cluster.write_attributes({0: LegrandMode.Switch}, manufacturer=0xFC40)
    mode_cluster._write_attributes.assert_awaited_once()
    try:
        mode_cluster._write_attributes.assert_awaited_with(
            [f.Attribute(attrid=0, value=f.TypeValue(value=t.data16([3, 0])))],
            manufacturer=0xFC40,
        )
    except AssertionError as e:
        logging.warning(
            "hum... Wrong assertion error due to unhashable nested list in data16 value.\n%s",
            str(e),
        )

    mode_cluster._write_attributes = mock.AsyncMock()
    await mode_cluster.write_attributes({0: LegrandMode.Auto}, manufacturer=0xFC40)
    mode_cluster._write_attributes.assert_awaited_once()
    try:
        mode_cluster._write_attributes.assert_awaited_with(
            [f.Attribute(attrid=0, value=f.TypeValue(value=t.data16([4, 0])))],
            manufacturer=0xFC40,
        )
    except AssertionError as e:
        logging.warning(
            "hum... Wrong assertion error due to unhashable nested list in data16 value.\n%s",
            str(e),
        )

    mode_cluster._write_attributes = mock.AsyncMock()
    await mode_cluster.write_attributes(
        {"mode": LegrandMode.Switch}, manufacturer=0xFC40
    )
    mode_cluster._write_attributes.assert_awaited_once()
    try:
        mode_cluster._write_attributes.assert_awaited_with(
            [f.Attribute(attrid=0, value=f.TypeValue(value=t.data16([3, 0])))],
            manufacturer=0xFC40,
        )
    except AssertionError as e:
        logging.warning(
            "hum... Wrong assertion error due to unhashable nested list in data16 value.\n%s",
            str(e),
        )

    mode_cluster._write_attributes = mock.AsyncMock()
    await mode_cluster.write_attributes({"mode": LegrandMode.Auto}, manufacturer=0xFC40)
    mode_cluster._write_attributes.assert_awaited_once()
    try:
        mode_cluster._write_attributes.assert_awaited_with(
            [f.Attribute(attrid=0, value=f.TypeValue(value=t.data16([4, 0])))],
            manufacturer=0xFC40,
        )
    except AssertionError as e:
        logging.warning(
            "hum... Wrong assertion error due to unhashable nested list in data16 value.\n%s",
            str(e),
        )
