"""Tests for the Elko Super TR child lock."""

from unittest import mock

import pytest
from zigpy.zcl import foundation
from zigpy.zcl.clusters.hvac import UserInterface

import zhaquirks
from zhaquirks.elko.smart_super_thermostat import CHILD_LOCK, ElkoSuperTRThermostat

zhaquirks.setup()


@pytest.mark.parametrize(
    "lockout, child_lock, expected_lockout",
    [
        (
            UserInterface.KeypadLockout.Level_1_lockout,
            True,
            UserInterface.KeypadLockout.Level_1_lockout,
        ),
        (
            UserInterface.KeypadLockout.Level_2_lockout,
            True,
            UserInterface.KeypadLockout.Level_1_lockout,
        ),
        (
            UserInterface.KeypadLockout.No_lockout,
            False,
            UserInterface.KeypadLockout.No_lockout,
        ),
    ],
)
async def test_keypad_lockout_writes_child_lock(
    zigpy_device_from_quirk, lockout, child_lock, expected_lockout
):
    """Writing the keypad lockout sends the child lock attribute to the device."""
    device = zigpy_device_from_quirk(ElkoSuperTRThermostat)
    thermostat = device.endpoints[1].thermostat
    ui = device.endpoints[1].thermostat_ui

    with mock.patch.object(
        thermostat,
        "write_attributes_raw",
        mock.AsyncMock(
            return_value=[
                [foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)]
            ]
        ),
    ) as write_raw:
        result = await ui.write_attributes({"keypad_lockout": lockout})

    assert result[0][0].status == foundation.Status.SUCCESS
    assert write_raw.await_count == 1
    (records,) = write_raw.await_args.args
    assert [(r.attrid, r.value.value) for r in records] == [(CHILD_LOCK, child_lock)]
    # Written without a manufacturer code, like Zigbee2MQTT does
    assert write_raw.await_args.kwargs == {"manufacturer_code": None}
    assert thermostat.get("child_lock") == child_lock
    assert ui.get("keypad_lockout") == expected_lockout


async def test_keypad_lockout_write_failure(zigpy_device_from_quirk):
    """A rejected child lock write is reported and leaves the lockout unchanged."""
    device = zigpy_device_from_quirk(ElkoSuperTRThermostat)
    thermostat = device.endpoints[1].thermostat
    ui = device.endpoints[1].thermostat_ui

    with mock.patch.object(
        thermostat,
        "write_attributes_raw",
        mock.AsyncMock(
            return_value=[
                [
                    foundation.WriteAttributesStatusRecord(
                        foundation.Status.READ_ONLY, CHILD_LOCK
                    )
                ]
            ]
        ),
    ) as write_raw:
        result = await ui.write_attributes(
            {"keypad_lockout": UserInterface.KeypadLockout.Level_1_lockout}
        )

    write_raw.assert_awaited_once()
    assert result[0][0].status == foundation.Status.READ_ONLY
    assert ui.get("keypad_lockout") is None


async def test_other_ui_attributes_stay_local(zigpy_device_from_quirk):
    """Other user interface attributes are written locally, not to the device."""
    device = zigpy_device_from_quirk(ElkoSuperTRThermostat)
    thermostat = device.endpoints[1].thermostat
    ui = device.endpoints[1].thermostat_ui

    with mock.patch.object(thermostat, "write_attributes_raw") as write_raw:
        result = await ui.write_attributes(
            {
                UserInterface.AttributeDefs.temperature_display_mode.name: (
                    UserInterface.TemperatureDisplayMode.Imperial
                )
            }
        )

    write_raw.assert_not_called()
    assert result[0][0].status == foundation.Status.SUCCESS
    assert (
        ui.get(UserInterface.AttributeDefs.temperature_display_mode.name)
        == UserInterface.TemperatureDisplayMode.Imperial
    )
    assert ui.get(UserInterface.AttributeDefs.keypad_lockout.name) is None
