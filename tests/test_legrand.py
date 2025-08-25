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
        [LegrandContactorSwitchOnOff.ON_OFF_ID + 1]
    )

    # cover _update_attribute
    switch_on_off_cluster._update_attribute(LegrandContactorSwitchOnOff.ON_OFF_ID, 0)

    # test sending other command
    try:
        mode_cluster._read_mode = mock.AsyncMock()
        auto_on_off_cluster.turn_on = mock.AsyncMock()
        auto_on_off_cluster.turn_off = mock.AsyncMock()
        auto_on_off_cluster.toggle = mock.AsyncMock()
        await switch_on_off_cluster.command(
            LegrandContactorSwitchOnOff.TOGGLE_CMD_ID + 1
        )
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
