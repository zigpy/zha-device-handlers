"""Tests for Namron quirks."""

from types import SimpleNamespace
from unittest import mock

import pytest
from zha.quirks import DEVICE_REGISTRY
from zigpy.device import Device
from zigpy.zcl import ClusterType, foundation
from zigpy.zcl.clusters.general import OnOff
from zigpy.zcl.clusters.hvac import (
    ControlSequenceOfOperation,
    RunningState,
    SystemMode,
    Thermostat,
    UserInterface,
)

import zhaquirks
from zhaquirks.builder.metadata import PreventDefaultEntityCreationMetadata
from zhaquirks.namron.thermostat_4512796 import (
    NamronOnOffCluster,
    NamronThermostatCluster,
    ProgramMode,
)

zhaquirks.setup()

SYSTEM_MODE_ID = Thermostat.AttributeDefs.system_mode.id
ON_OFF_ID = OnOff.AttributeDefs.on_off.id


@pytest.fixture(params=["4512795", "4512796"])
def thermostat_device(
    zigpy_device_from_v2_quirk, request: pytest.FixtureRequest
) -> Device:
    """Namron Simplify thermostat, in both color variants, with the quirk applied."""
    return zigpy_device_from_v2_quirk(
        "Namron AS",
        request.param,
        cluster_ids={
            1: {
                OnOff.cluster_id: ClusterType.Server,
                Thermostat.cluster_id: ClusterType.Server,
            }
        },
    )


def test_thermostat_clusters_replaced(thermostat_device: Device) -> None:
    """The quirk swaps in the custom thermostat and OnOff clusters."""
    endpoint = thermostat_device.endpoints[1]
    assert isinstance(endpoint.thermostat, NamronThermostatCluster)
    assert isinstance(endpoint.on_off, NamronOnOffCluster)


@pytest.mark.parametrize(
    ("raw", "program_mode"),
    [
        pytest.param(0x00, ProgramMode.Manual, id="manual"),
        pytest.param(0x01, ProgramMode.Home, id="home"),
        pytest.param(0x02, ProgramMode.Away, id="away"),
        pytest.param(0x03, ProgramMode.Sleep, id="sleep"),
        pytest.param(0x04, ProgramMode.Holiday, id="holiday"),
    ],
)
@pytest.mark.parametrize(
    ("on_off", "system_mode"),
    [
        pytest.param(True, SystemMode.Heat, id="on"),
        pytest.param(False, SystemMode.Off, id="off"),
    ],
)
def test_system_mode_report_sets_program_mode(
    thermostat_device: Device,
    raw: int,
    program_mode: ProgramMode,
    on_off: bool,
    system_mode: SystemMode,
) -> None:
    """A raw `system_mode` report becomes the program, with Off/Heat from OnOff."""
    endpoint = thermostat_device.endpoints[1]
    endpoint.on_off.update_attribute(ON_OFF_ID, on_off)

    endpoint.thermostat.update_attribute(SYSTEM_MODE_ID, raw)

    assert endpoint.thermostat.get("program_mode") == program_mode
    assert endpoint.thermostat.get("system_mode") == system_mode


def test_system_mode_defaults_to_heat_without_on_off(thermostat_device: Device) -> None:
    """Before OnOff is known, the thermostat is assumed to be heating."""
    thermostat = thermostat_device.endpoints[1].thermostat

    thermostat.update_attribute(SYSTEM_MODE_ID, ProgramMode.Sleep)

    assert thermostat.get("system_mode") == SystemMode.Heat


def test_on_off_report_updates_system_mode(thermostat_device: Device) -> None:
    """Turning the device off and on is mirrored in `system_mode`."""
    endpoint = thermostat_device.endpoints[1]
    endpoint.thermostat.update_attribute(SYSTEM_MODE_ID, ProgramMode.Home)

    endpoint.on_off.update_attribute(ON_OFF_ID, False)
    assert endpoint.thermostat.get("system_mode") == SystemMode.Off

    endpoint.on_off.update_attribute(ON_OFF_ID, True)
    assert endpoint.thermostat.get("system_mode") == SystemMode.Heat
    # The program is unaffected by power state
    assert endpoint.thermostat.get("program_mode") == ProgramMode.Home


def test_ctrl_sequence_of_oper_is_heating_only(thermostat_device: Device) -> None:
    """The reported Cooling_and_Heating sequence is replaced with Heating_Only."""
    thermostat = thermostat_device.endpoints[1].thermostat

    thermostat.update_attribute(
        Thermostat.AttributeDefs.ctrl_sequence_of_oper.id,
        ControlSequenceOfOperation.Cooling_and_Heating,
    )

    assert (
        thermostat.get("ctrl_sequence_of_oper")
        == ControlSequenceOfOperation.Heating_Only
    )


@pytest.mark.parametrize(
    ("raw", "running_state"),
    [
        pytest.param(0x0000, RunningState.Heat_State_On, id="heating"),
        pytest.param(0x0010, RunningState.Idle, id="idle"),
    ],
)
def test_running_state_is_inverted(
    thermostat_device: Device, raw: int, running_state: RunningState
) -> None:
    """The device's inverted running state is translated to heating/idle."""
    thermostat = thermostat_device.endpoints[1].thermostat

    thermostat.update_attribute(Thermostat.AttributeDefs.running_state.id, raw)

    assert thermostat.get("running_state") == running_state


@pytest.mark.parametrize(
    "attribute",
    [
        Thermostat.AttributeDefs.pi_heating_demand,
        Thermostat.AttributeDefs.pi_cooling_demand,
    ],
)
def test_pi_demand_is_ignored(
    thermostat_device: Device, attribute: foundation.ZCLAttributeDef
) -> None:
    """PI demands stay unset so ZHA derives the HVAC action from running_state."""
    thermostat = thermostat_device.endpoints[1].thermostat
    # Simulate a value cached before the quirk was applied
    thermostat._attr_cache.set_value(attribute, 0)

    thermostat.update_attribute(attribute.id, 0)

    assert thermostat.get(attribute.name) is None


def test_default_entities_suppressed(thermostat_device: Device) -> None:
    """The empty demand sensor, on/off switch and keypad lockout select are hidden."""
    entry = DEVICE_REGISTRY.match_entry(thermostat_device)
    pi_demand, switch, keypad_lockout = (
        entry.zha_device_factory.quirk_definition.disabled_default_entities
    )

    assert pi_demand == PreventDefaultEntityCreationMetadata(
        endpoint_id=1,
        cluster_id=Thermostat.cluster_id,
        cluster_type=ClusterType.Server,
        unique_id_suffix="pi_heating_demand",
        function=None,
    )

    assert switch.endpoint_id == 1
    assert switch.cluster_id == OnOff.cluster_id
    assert switch.cluster_type == ClusterType.Server
    assert switch.function(SimpleNamespace(translation_key="switch"))
    # The start-up behavior select on the same cluster is kept
    assert not switch.function(SimpleNamespace(translation_key="start_up_on_off"))

    assert keypad_lockout.endpoint_id == 1
    assert keypad_lockout.cluster_id == UserInterface.cluster_id
    assert keypad_lockout.function(SimpleNamespace(translation_key="keypad_lockout"))
    # The replacement child lock switch on the same attribute is kept
    assert not keypad_lockout.function(SimpleNamespace(translation_key="child_lock"))


def test_child_lock_switch(thermostat_device: Device) -> None:
    """Keypad lockout is exposed as an Unlock/Lock1 switch."""
    entry = DEVICE_REGISTRY.match_entry(thermostat_device)
    (child_lock,) = (
        meta
        for meta in entry.zha_device_factory.quirk_definition.entity_metadata
        if meta.translation_key == "child_lock"
    )

    assert child_lock.cluster_id == UserInterface.cluster_id
    assert child_lock.attribute_name == "keypad_lockout"
    assert (child_lock.off_value, child_lock.on_value) == (0, 1)


PRESET_TEMPERATURES = pytest.mark.parametrize(
    ("attribute", "attrid", "raw"),
    [
        pytest.param("home_temperature", 0x8039, 190, id="home"),
        pytest.param("away_temperature", 0x8036, 185, id="away"),
        pytest.param("sleep_temperature", 0x803B, 170, id="sleep"),
        pytest.param("holiday_temperature", 0x8013, 1600, id="holiday"),
    ],
)


@PRESET_TEMPERATURES
def test_preset_temperature_report(
    thermostat_device: Device, attribute: str, attrid: int, raw: int
) -> None:
    """Captured preset setpoint reports decode to their attributes."""
    thermostat = thermostat_device.endpoints[1].thermostat

    thermostat.update_attribute(attrid, raw)

    assert thermostat.get(attribute) == raw


@pytest.mark.parametrize(
    ("attribute", "multiplier"),
    [
        pytest.param("home_temperature", 0.1, id="home"),
        pytest.param("away_temperature", 0.1, id="away"),
        pytest.param("sleep_temperature", 0.1, id="sleep"),
        pytest.param("holiday_temperature", 0.01, id="holiday"),
    ],
)
def test_preset_temperature_number(
    thermostat_device: Device, attribute: str, multiplier: float
) -> None:
    """Each preset setpoint is exposed as a °C number entity with its scale."""
    entry = DEVICE_REGISTRY.match_entry(thermostat_device)
    (number,) = (
        meta
        for meta in entry.zha_device_factory.quirk_definition.entity_metadata
        if getattr(meta, "attribute_name", None) == attribute
    )

    assert number.multiplier == multiplier
    assert (number.min, number.max, number.step) == (5, 40, 0.5)


@PRESET_TEMPERATURES
async def test_write_preset_temperature(
    thermostat_device: Device, attribute: str, attrid: int, raw: int
) -> None:
    """Preset setpoints are written without a manufacturer code."""
    thermostat = thermostat_device.endpoints[1].thermostat

    with mock.patch.object(
        thermostat,
        "_write_attributes",
        mock.AsyncMock(
            return_value=[
                [foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)]
            ]
        ),
    ) as write_mock:
        await thermostat.write_attributes({attribute: raw})

    written = write_mock.call_args[0][0]
    assert written[0].attrid == attrid
    assert written[0].value.value == raw
    assert write_mock.call_args.kwargs["manufacturer"] is None
    assert thermostat.get(attribute) == raw


async def test_write_program_mode(thermostat_device: Device) -> None:
    """Writing `program_mode` writes the raw value to `system_mode`."""
    endpoint = thermostat_device.endpoints[1]
    endpoint.on_off.update_attribute(ON_OFF_ID, True)
    thermostat = endpoint.thermostat

    with mock.patch.object(
        thermostat,
        "_write_attributes",
        mock.AsyncMock(
            return_value=[
                [foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)]
            ]
        ),
    ) as write_mock:
        result = await thermostat.write_attributes({"program_mode": ProgramMode.Away})

    written = write_mock.call_args[0][0]
    assert len(written) == 1
    assert written[0].attrid == SYSTEM_MODE_ID
    assert written[0].value.value == ProgramMode.Away
    assert result == [
        [
            foundation.WriteAttributesStatusRecord(
                foundation.Status.SUCCESS,
                NamronThermostatCluster.AttributeDefs.program_mode.id,
            )
        ]
    ]
    assert thermostat.get("program_mode") == ProgramMode.Away
    assert thermostat.get("system_mode") == SystemMode.Heat


@pytest.mark.parametrize(
    ("current", "requested", "written"),
    [
        pytest.param(
            ProgramMode.Home,
            ProgramMode.Home,
            [ProgramMode.Manual, ProgramMode.Home],
            id="reselect_preset",
        ),
        pytest.param(
            ProgramMode.Manual,
            ProgramMode.Manual,
            [ProgramMode.Manual],
            id="reselect_manual",
        ),
        pytest.param(
            ProgramMode.Home,
            ProgramMode.Sleep,
            [ProgramMode.Sleep],
            id="change_preset",
        ),
    ],
)
async def test_write_program_mode_clears_override(
    thermostat_device: Device,
    current: ProgramMode,
    requested: ProgramMode,
    written: list[ProgramMode],
) -> None:
    """Re-selecting the active preset steps through Manual so the device reacts."""
    thermostat = thermostat_device.endpoints[1].thermostat
    thermostat.update_attribute(SYSTEM_MODE_ID, current)

    with mock.patch.object(
        thermostat,
        "_write_attributes",
        mock.AsyncMock(
            return_value=[
                [foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)]
            ]
        ),
    ) as write_mock:
        await thermostat.write_attributes({"program_mode": requested})

    assert [call.args[0][0].value.value for call in write_mock.call_args_list] == (
        written
    )
    assert thermostat.get("program_mode") == requested


async def test_write_program_mode_stops_on_failed_step(
    thermostat_device: Device,
) -> None:
    """If stepping through Manual fails, the preset is not rewritten."""
    thermostat = thermostat_device.endpoints[1].thermostat
    thermostat.update_attribute(SYSTEM_MODE_ID, ProgramMode.Home)

    with mock.patch.object(
        thermostat,
        "_write_attributes",
        mock.AsyncMock(
            return_value=[
                [
                    foundation.WriteAttributesStatusRecord(
                        foundation.Status.FAILURE, SYSTEM_MODE_ID
                    )
                ]
            ]
        ),
    ) as write_mock:
        result = await thermostat.write_attributes({"program_mode": ProgramMode.Home})

    assert write_mock.call_count == 1
    assert result == [
        [
            foundation.WriteAttributesStatusRecord(
                foundation.Status.FAILURE,
                NamronThermostatCluster.AttributeDefs.program_mode.id,
            )
        ]
    ]
    assert thermostat.get("program_mode") == ProgramMode.Home


@pytest.mark.parametrize(
    ("system_mode", "command_id", "on_off"),
    [
        pytest.param(SystemMode.Off, OnOff.ServerCommandDefs.off.id, False, id="off"),
        pytest.param(SystemMode.Heat, OnOff.ServerCommandDefs.on.id, True, id="heat"),
    ],
)
async def test_write_system_mode_sends_on_off(
    thermostat_device: Device, system_mode: SystemMode, command_id: int, on_off: bool
) -> None:
    """Writing `system_mode` turns the device on or off instead."""
    endpoint = thermostat_device.endpoints[1]
    endpoint.thermostat.update_attribute(SYSTEM_MODE_ID, ProgramMode.Home)

    with (
        mock.patch.object(
            endpoint.on_off,
            "request",
            mock.AsyncMock(
                return_value=foundation.GENERAL_COMMANDS[
                    foundation.GeneralCommand.Default_Response
                ].schema(command_id=command_id, status=foundation.Status.SUCCESS)
            ),
        ) as request_mock,
        mock.patch.object(endpoint.thermostat, "_write_attributes") as write_mock,
    ):
        result = await endpoint.thermostat.write_attributes(
            {"system_mode": system_mode}
        )

    write_mock.assert_not_called()
    assert request_mock.call_args[0][1] == command_id
    assert result == [
        [
            foundation.WriteAttributesStatusRecord(
                foundation.Status.SUCCESS, SYSTEM_MODE_ID
            )
        ]
    ]
    assert endpoint.on_off.get("on_off") == on_off
    assert endpoint.thermostat.get("system_mode") == system_mode
    assert endpoint.thermostat.get("program_mode") == ProgramMode.Home


async def test_read_program_mode_reads_system_mode(thermostat_device: Device) -> None:
    """Reading `program_mode` is served by a `system_mode` read."""
    thermostat = thermostat_device.endpoints[1].thermostat

    with mock.patch.object(
        thermostat,
        "_read_attributes",
        mock.AsyncMock(
            return_value=(
                [
                    foundation.ReadAttributeRecord(
                        SYSTEM_MODE_ID,
                        foundation.Status.SUCCESS,
                        foundation.TypeValue(None, SystemMode(0x03)),
                    )
                ],
            )
        ),
    ) as read_mock:
        success, failure = await thermostat.read_attributes(
            ["program_mode"], allow_cache=True
        )

    assert read_mock.call_args[0][0] == [SYSTEM_MODE_ID]
    assert success == {"program_mode": ProgramMode.Sleep}
    assert failure == {}


def _read_response(
    attrid: int, status: foundation.Status, value: object = None
) -> tuple[list[foundation.ReadAttributeRecord]]:
    return (
        [
            foundation.ReadAttributeRecord(
                attrid, status, foundation.TypeValue(None, value)
            )
        ],
    )


async def test_read_without_program_mode_is_unchanged(
    thermostat_device: Device,
) -> None:
    """Reads that do not include `program_mode` go straight to the device."""
    thermostat = thermostat_device.endpoints[1].thermostat
    local_temperature_id = Thermostat.AttributeDefs.local_temperature.id

    with mock.patch.object(
        thermostat,
        "_read_attributes",
        mock.AsyncMock(
            return_value=_read_response(
                local_temperature_id, foundation.Status.SUCCESS, 2150
            )
        ),
    ) as read_mock:
        success, failure = await thermostat.read_attributes(["local_temperature"])

    assert read_mock.call_args[0][0] == [local_temperature_id]
    assert success == {"local_temperature": 2150}
    assert failure == {}


async def test_read_program_mode_with_other_attributes(
    thermostat_device: Device,
) -> None:
    """Other attributes in the same read are read as usual."""
    thermostat = thermostat_device.endpoints[1].thermostat
    local_temperature_id = Thermostat.AttributeDefs.local_temperature.id

    with mock.patch.object(
        thermostat,
        "_read_attributes",
        mock.AsyncMock(
            side_effect=[
                _read_response(local_temperature_id, foundation.Status.SUCCESS, 2150),
                _read_response(
                    SYSTEM_MODE_ID, foundation.Status.SUCCESS, ProgramMode.Away
                ),
            ]
        ),
    ) as read_mock:
        success, failure = await thermostat.read_attributes(
            ["local_temperature", "program_mode"]
        )

    assert [call.args[0] for call in read_mock.call_args_list] == [
        [local_temperature_id],
        [SYSTEM_MODE_ID],
    ]
    assert success == {"local_temperature": 2150, "program_mode": ProgramMode.Away}
    assert failure == {}


async def test_read_program_mode_failure(thermostat_device: Device) -> None:
    """A failed `system_mode` read is reported as a failed `program_mode` read."""
    thermostat = thermostat_device.endpoints[1].thermostat

    with mock.patch.object(
        thermostat,
        "_read_attributes",
        mock.AsyncMock(
            return_value=_read_response(
                SYSTEM_MODE_ID, foundation.Status.UNSUPPORTED_ATTRIBUTE
            )
        ),
    ):
        success, failure = await thermostat.read_attributes(["program_mode"])

    assert success == {}
    assert failure == {"program_mode": foundation.Status.FAILURE}
