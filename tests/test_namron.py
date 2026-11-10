"""Tests for Namron quirks."""

from collections.abc import AsyncIterator
from unittest import mock

import pytest
from zha.application import Platform
from zha.application.platforms.climate.const import HVACAction
from zha.quirks import DEVICE_REGISTRY
from zha.zigbee.device import ZigbeeDevice
from zigpy.device import Device
import zigpy.types as t
from zigpy.zcl import ClusterType, foundation
from zigpy.zcl.clusters.general import OnOff
from zigpy.zcl.clusters.hvac import (
    ControlSequenceOfOperation,
    RunningState,
    SystemMode,
    Thermostat,
    UserInterface,
)

from tests.zha_helpers import join_device_from_diagnostics, zha_gateway
import zhaquirks
from zhaquirks.builder import EntityFilter
from zhaquirks.namron.remote_4512793 import NamronPrivateRemoteCluster
from zhaquirks.namron.thermostat_4512796 import (
    NamronOnOffCluster,
    NamronThermostatCluster,
    ProgramMode,
)

zhaquirks.setup()

SYSTEM_MODE_ID = Thermostat.AttributeDefs.system_mode.id
ON_OFF_ID = OnOff.AttributeDefs.on_off.id
THERMOSTAT_DIAGNOSTICS = "namron-as-4512796-0x00000019.json"
THERMOSTAT_IEEE = "00:11:22:33:44:55:66:77"
CLIMATE_UNIQUE_ID = f"{THERMOSTAT_IEEE}-1"
PROGRAM_MODE_UNIQUE_ID = f"{THERMOSTAT_IEEE}-1-program_mode"


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
    assert entry.zha_device_factory.quirk_definition.disabled_default_entities == (
        EntityFilter(
            endpoint_id=1,
            cluster_id=Thermostat.cluster_id,
            unique_id_suffix="pi_heating_demand",
        ),
        EntityFilter(
            endpoint_id=1, cluster_id=OnOff.cluster_id, translation_key="switch"
        ),
        EntityFilter(
            endpoint_id=1,
            cluster_id=UserInterface.cluster_id,
            translation_key="keypad_lockout",
        ),
    )


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


@pytest.fixture
async def zha_thermostat() -> AsyncIterator[ZigbeeDevice]:
    """Namron thermostat joined to a ZHA gateway from its diagnostics."""
    async with zha_gateway() as gateway:
        yield await join_device_from_diagnostics(
            gateway, THERMOSTAT_DIAGNOSTICS, DEVICE_REGISTRY
        )


def test_zha_entities(zha_thermostat: ZigbeeDevice) -> None:
    """ZHA creates the quirk's entities in place of the removed defaults."""
    entities = zha_thermostat.platform_entities

    assert {
        f"{THERMOSTAT_IEEE}-1-{suffix}"
        for suffix in (
            "keypad_lockout",
            "program_mode",
            "home_temperature",
            "away_temperature",
            "sleep_temperature",
            "holiday_temperature",
        )
    } <= {unique_id for _, unique_id in entities}
    assert {entity.translation_key for entity in entities.values()}.isdisjoint(
        {"switch", "keypad_lockout", "pi_heating_demand"}
    )


async def test_zha_interview_skips_virtual_attribute(
    zha_thermostat: ZigbeeDevice,
) -> None:
    """The virtual `program_mode` is never read from the device."""
    thermostat = zha_thermostat.device.endpoints[1].thermostat

    await zha_thermostat.async_configure()
    await zha_thermostat.async_initialize(from_cache=False)
    await zha_thermostat.gateway.async_block_till_done()

    read = [
        attr_id
        for call in thermostat.read_attributes_raw.call_args_list
        for attr_id in call.args[0]
    ]
    assert SYSTEM_MODE_ID in read
    assert NamronThermostatCluster.AttributeDefs.program_mode.id not in read


@pytest.mark.parametrize(
    ("hvac_mode", "initial_on_off", "command_id", "system_mode"),
    [
        pytest.param(
            "off", True, OnOff.ServerCommandDefs.off.id, SystemMode.Off, id="off"
        ),
        pytest.param(
            "heat", False, OnOff.ServerCommandDefs.on.id, SystemMode.Heat, id="heat"
        ),
    ],
)
async def test_zha_hvac_mode_uses_on_off(
    zha_thermostat: ZigbeeDevice,
    hvac_mode: str,
    initial_on_off: bool,
    command_id: int,
    system_mode: SystemMode,
) -> None:
    """The climate entity's HVAC mode is applied through the OnOff cluster."""
    endpoint = zha_thermostat.device.endpoints[1]
    endpoint.on_off.update_attribute(ON_OFF_ID, initial_on_off)
    default_response = foundation.GENERAL_COMMANDS[
        foundation.GeneralCommand.Default_Response
    ].schema(command_id=command_id, status=foundation.Status.SUCCESS)
    climate = zha_thermostat.get_platform_entity(
        Platform.CLIMATE, unique_id=CLIMATE_UNIQUE_ID
    )

    with mock.patch.object(
        endpoint.on_off, "command", mock.AsyncMock(return_value=default_response)
    ) as command_mock:
        await climate.async_set_hvac_mode(hvac_mode)
        await zha_thermostat.gateway.async_block_till_done()

    command_mock.assert_awaited_once_with(command_id)
    assert endpoint.thermostat.get(SYSTEM_MODE_ID) == system_mode
    assert climate.hvac_mode == hvac_mode


async def test_zha_preset_select_writes_system_mode(
    zha_thermostat: ZigbeeDevice,
) -> None:
    """The preset select writes the raw program to `system_mode`."""
    endpoint = zha_thermostat.device.endpoints[1]
    thermostat = endpoint.thermostat
    endpoint.on_off.update_attribute(ON_OFF_ID, True)
    thermostat.update_attribute(SYSTEM_MODE_ID, ProgramMode.Manual)
    select = zha_thermostat.get_platform_entity(
        Platform.SELECT, unique_id=PROGRAM_MODE_UNIQUE_ID
    )
    climate = zha_thermostat.get_platform_entity(
        Platform.CLIMATE, unique_id=CLIMATE_UNIQUE_ID
    )

    with mock.patch.object(
        thermostat,
        "_write_attributes",
        mock.AsyncMock(
            return_value=[
                [foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)]
            ]
        ),
    ) as write_mock:
        await select.async_select_option(ProgramMode.Away.name)
        await zha_thermostat.gateway.async_block_till_done()

    (record,) = write_mock.call_args[0][0]
    assert record.attrid == SYSTEM_MODE_ID
    assert record.value.value == ProgramMode.Away
    assert select.current_option == ProgramMode.Away.name
    assert climate.hvac_mode == "heat"


@pytest.mark.parametrize(
    ("running_state", "hvac_action"),
    [
        pytest.param(RunningState.Cool_2nd_Stage_On, HVACAction.IDLE, id="idle"),
        pytest.param(0x0000, HVACAction.HEATING, id="heating"),
    ],
)
async def test_zha_hvac_action_follows_running_state(
    zha_thermostat: ZigbeeDevice, running_state: int, hvac_action: HVACAction
) -> None:
    """The HVAC action reflects the corrected `running_state` report."""
    endpoint = zha_thermostat.device.endpoints[1]
    endpoint.on_off.update_attribute(ON_OFF_ID, True)
    climate = zha_thermostat.get_platform_entity(
        Platform.CLIMATE, unique_id=CLIMATE_UNIQUE_ID
    )

    endpoint.thermostat.update_attribute(
        Thermostat.AttributeDefs.running_state.id, running_state
    )

    assert climate.hvac_action == hvac_action


@pytest.mark.parametrize(
    "payload, event_name, event_args",
    [
        (
            b"\x01\x01",
            "button_1_remote_button_short_press",
            {"button": "button_1", "press_type": "remote_button_short_press"},
        ),
        (
            b"\x01\x02",
            "button_1_remote_button_long_press",
            {"button": "button_1", "press_type": "remote_button_long_press"},
        ),
        (
            b"\x01\x04",
            "button_1_remote_button_long_release",
            {"button": "button_1", "press_type": "remote_button_long_release"},
        ),
        (
            b"\x06\x01",
            "button_6_remote_button_short_press",
            {"button": "button_6", "press_type": "remote_button_short_press"},
        ),
        (
            b"\x03\x02",
            "button_3_remote_button_long_press",
            {"button": "button_3", "press_type": "remote_button_long_press"},
        ),
    ],
)
async def test_button_triggers(
    zigpy_device_from_v2_quirk, payload, event_name, event_args
):
    """Test that real captured button/action payloads produce the right zha_event."""
    device = zigpy_device_from_v2_quirk("Namron AS", "4512793")
    cluster = device.endpoints[1].namron_private_remote
    listener = mock.MagicMock()
    cluster.add_listener(listener)

    # Real captured frame header: frame_control=0x19, tsn=<any>, command_id=0x00
    header = b"\x19" + bytes([0x42]) + b"\x00"
    device.packet_received(
        t.ZigbeePacket(
            profile_id=260,
            cluster_id=NamronPrivateRemoteCluster.cluster_id,
            src_ep=1,
            dst_ep=1,
            data=t.SerializableBytes(header + payload),
        )
    )

    assert listener.zha_send_event.call_count == 1
    assert listener.zha_send_event.call_args == mock.call(event_name, event_args)


async def test_unknown_button_and_action_discarded(zigpy_device_from_v2_quirk):
    """Unrecognized button/action values should not raise or emit an event."""
    device = zigpy_device_from_v2_quirk("Namron AS", "4512793")
    cluster = device.endpoints[1].namron_private_remote
    listener = mock.MagicMock()
    cluster.add_listener(listener)

    header = b"\x19" + bytes([0x42]) + b"\x00"
    device.packet_received(
        t.ZigbeePacket(
            profile_id=260,
            cluster_id=NamronPrivateRemoteCluster.cluster_id,
            src_ep=1,
            dst_ep=1,
            data=t.SerializableBytes(header + b"\x09\x09"),
        )
    )

    assert listener.zha_send_event.call_count == 0


async def test_unrelated_command_falls_through(zigpy_device_from_v2_quirk):
    """A command other than button_action should fall through to the base handler."""
    device = zigpy_device_from_v2_quirk("Namron AS", "4512793")
    cluster = device.endpoints[1].namron_private_remote
    listener = mock.MagicMock()
    cluster.add_listener(listener)

    # command_id 0x01, not button_action (0x00)
    header = b"\x19" + bytes([0x42]) + b"\x01"
    device.packet_received(
        t.ZigbeePacket(
            profile_id=260,
            cluster_id=NamronPrivateRemoteCluster.cluster_id,
            src_ep=1,
            dst_ep=1,
            data=t.SerializableBytes(header),
        )
    )

    assert listener.zha_send_event.call_count == 0
