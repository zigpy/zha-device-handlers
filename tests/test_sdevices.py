"""Tests for SDevices quirks."""

from unittest import mock

import pytest
from zigpy.profiles import zha
from zigpy.zcl import ClusterType, ReportingConfig, foundation
from zigpy.zcl.clusters.closures import WindowCovering, WindowCoveringMode
from zigpy.zcl.clusters.general import DeviceTemperature, MultistateInput, OnOff
from zigpy.zcl.clusters.homeautomation import Diagnostic
from zigpy.zcl.clusters.hvac import Thermostat, UserInterface

import zhaquirks
from zhaquirks.builder.metadata import NumberMetadata, SwitchMetadata, ZCLEnumMetadata
from zhaquirks.clusters import CustomCluster
from zhaquirks.const import (
    BUTTON_1,
    BUTTON_2,
    COMMAND,
    DOUBLE_PRESS,
    LONG_PRESS,
    SHORT_PRESS,
)
from zhaquirks.sdevices import (
    SDevicesButtonCluster,
    SDevicesCluster,
    SDevicesDeviceTemperatureCluster,
    SDevicesOnOffCluster,
    SDevicesTwoButtonCluster,
    SDevicesWindowCoveringCluster,
)
from zhaquirks.sdevices.socket import _socket
from zhaquirks.sdevices.switch import _single_button_switch, _two_button_switch
from zhaquirks.sdevices.thermostat import (
    SDevicesProgrammingOperationMode,
    SDevicesThermostatCluster,
    _thermostat,
)

zhaquirks.setup()

PRESENT_VALUE = MultistateInput.AttributeDefs.present_value.id


def _make_thermostat(zigpy_device_from_v2_quirk) -> SDevicesThermostatCluster:
    """Create an SBDV-00205 with its standard Thermostat server cluster."""
    device = zigpy_device_from_v2_quirk(
        "SDevices",
        "SBDV-00205",
        cluster_ids={1: {Thermostat.cluster_id: ClusterType.Server}},
    )
    cluster = device.endpoints[1].thermostat
    assert isinstance(cluster, SDevicesThermostatCluster)
    return cluster


def test_thermostat_schedule_attributes(zigpy_device_from_v2_quirk):
    """The thermostat exposes one local string schedule for every weekday."""
    cluster = _make_thermostat(zigpy_device_from_v2_quirk)

    assert [
        getattr(cluster.AttributeDefs, name).id
        for name in (
            "schedule_monday",
            "schedule_tuesday",
            "schedule_wednesday",
            "schedule_thursday",
            "schedule_friday",
            "schedule_saturday",
            "schedule_sunday",
        )
    ] == list(range(0xF100, 0xF107))

    assert {
        cluster.find_attribute(attr_id).name
        for attr_id in cluster._SCHEDULE_ATTR_TO_DAY  # noqa: SLF001
    } == {
        "schedule_sunday",
        "schedule_monday",
        "schedule_tuesday",
        "schedule_wednesday",
        "schedule_thursday",
        "schedule_friday",
        "schedule_saturday",
    }


def test_thermostat_programming_mode_select_uses_server_cluster():
    """The mode select avoids the duplicate client-side Thermostat cluster."""
    (metadata,) = (
        entity
        for entity in _thermostat.entity_metadata
        if isinstance(entity, ZCLEnumMetadata)
        and entity.attribute_name == Thermostat.AttributeDefs.programing_oper_mode.name
    )

    assert metadata.cluster_type is ClusterType.Server
    assert metadata.enum is SDevicesProgrammingOperationMode
    assert metadata.attribute_initialized_from_cache is False


def test_thermostat_keypad_lockout_is_binary_switch():
    """Expose the firmware's binary lockout behavior as a switch."""
    (metadata,) = (
        entity
        for entity in _thermostat.entity_metadata
        if isinstance(entity, SwitchMetadata)
        and entity.attribute_name == UserInterface.AttributeDefs.keypad_lockout.name
    )

    assert metadata.cluster_id == UserInterface.cluster_id
    assert metadata.off_value == 0
    assert metadata.on_value == 1
    assert metadata.translation_key == "child_lock"
    assert any(
        disabled.cluster_id == UserInterface.cluster_id
        and disabled.function is not None
        for disabled in _thermostat.disabled_default_entities
    )


def test_thermostat_status_bitmaps_update_boolean_attributes(
    zigpy_device_from_v2_quirk,
):
    """Status bitmaps are split into the individual diagnostic flags."""
    cluster = _make_thermostat(zigpy_device_from_v2_quirk)

    cluster._update_attribute(cluster.AttributeDefs.sensor_error.id, None)  # noqa: SLF001
    cluster._update_attribute(cluster.AttributeDefs.sensor_error.id, 0b101)
    cluster._update_attribute(cluster.AttributeDefs.event_status.id, 0b1010)
    cluster._update_attribute(0xFFFF, 1)  # noqa: SLF001

    assert cluster.get("sensor_error_remote_disconnected") is True
    assert cluster.get("sensor_error_local_disconnected") is False
    assert cluster.get("sensor_error_short_circuit") is True
    assert cluster.get("status_heat_inefficient") is False
    assert cluster.get("status_antifrost") is True
    assert cluster.get("status_open_window") is False
    assert cluster.get("status_invalid_time") is True


def test_thermostat_schedule_helpers_validate_and_format():
    """Schedule helper methods reject malformed data and format transitions."""
    with pytest.raises(TypeError, match="Schedule must be a string"):
        SDevicesThermostatCluster._parse_schedule(None)

    with pytest.raises(ValueError, match="Expected 2 schedule values"):
        SDevicesThermostatCluster._format_schedule([360], 1)

    assert SDevicesThermostatCluster._format_schedule([1080, 1750], 1) == "18:00/17.5"


@pytest.mark.asyncio
async def test_thermostat_mixed_schedule_read_and_write(
    zigpy_device_from_v2_quirk,
):
    """Regular attributes continue to use the base read/write implementation."""
    cluster = _make_thermostat(zigpy_device_from_v2_quirk)
    cluster.update_attribute(
        Thermostat.AttributeDefs.local_temperature.id,
        2000,
    )
    cluster.command = mock.AsyncMock()

    success, failure = await cluster.read_attributes(
        [Thermostat.AttributeDefs.local_temperature.name, "schedule_monday"],
        only_cache=True,
    )

    assert success["schedule_monday"] is None
    assert failure == {}
    assert cluster.command.await_count == 0

    regular_result = [
        foundation.WriteAttributesStatusRecord(status=foundation.Status.SUCCESS)
    ]
    with mock.patch.object(
        CustomCluster,
        "write_attributes",
        new=mock.AsyncMock(return_value=[regular_result]),
    ):
        result = await cluster.write_attributes(
            {
                Thermostat.AttributeDefs.local_temperature.name: 2000,
                "schedule_monday": "06:00/20",
            }
        )

    assert len(result[0]) == 2


@pytest.mark.parametrize(
    "mode, values, count",
    (
        (Thermostat.SeqMode.Cool, [1080, 1750], 1),
        (Thermostat.SeqMode.Heat, [], 1),
    ),
)
def test_thermostat_ignores_unsupported_schedule_responses(
    zigpy_device_from_v2_quirk, mode, values, count
):
    """Unsupported modes and malformed responses do not update local schedules."""
    cluster = _make_thermostat(zigpy_device_from_v2_quirk)
    hdr = mock.Mock(
        command_id=Thermostat.ClientCommandDefs.get_weekly_schedule_response.id
    )
    args = mock.Mock(
        day_of_week_for_sequence=Thermostat.SeqDayOfWeek.Monday,
        mode_for_sequence=mode,
        values=values,
        num_transitions_for_sequence=count,
    )

    cluster.handle_cluster_request(hdr, args)

    assert cluster.get("schedule_monday") is None


def test_thermostat_delegates_unknown_cluster_commands(
    zigpy_device_from_v2_quirk,
):
    """Unknown commands retain the standard cluster handling."""
    cluster = _make_thermostat(zigpy_device_from_v2_quirk)
    cluster.handle_cluster_request(mock.Mock(command_id=0xFF), object())


@pytest.mark.asyncio
async def test_thermostat_schedule_write_groups_identical_days(
    zigpy_device_from_v2_quirk,
):
    """Identical day schedules are sent as one standard ZCL schedule command."""
    cluster = _make_thermostat(zigpy_device_from_v2_quirk)
    cluster.command = mock.AsyncMock()
    schedule = "18:00/17.5 06:00/20"

    result = await cluster.write_attributes(
        {
            "schedule_monday": schedule,
            "schedule_tuesday": schedule,
        }
    )

    set_days = Thermostat.SeqDayOfWeek.Monday | Thermostat.SeqDayOfWeek.Tuesday
    assert cluster.command.await_args_list == [
        mock.call(
            Thermostat.ServerCommandDefs.set_weekly_schedule.id,
            2,
            set_days,
            Thermostat.SeqMode.Heat,
            [360, 2000, 1080, 1750],
            expect_reply=False,
        ),
        mock.call(
            Thermostat.ServerCommandDefs.get_weekly_schedule.id,
            Thermostat.SeqDayOfWeek.Monday,
            Thermostat.SeqMode.Heat,
            expect_reply=False,
        ),
        mock.call(
            Thermostat.ServerCommandDefs.get_weekly_schedule.id,
            Thermostat.SeqDayOfWeek.Tuesday,
            Thermostat.SeqMode.Heat,
            expect_reply=False,
        ),
    ]
    assert cluster.get("schedule_monday") == schedule
    assert cluster.get("schedule_tuesday") == schedule
    assert all(record.status == foundation.Status.SUCCESS for record in result[0])


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "schedule, error",
    (
        ("6:00/20", "HH:MM/temperature"),
        ("06:00/20.1", "HH:MM/temperature"),
        ("06:00/50.5", "between 0 and 50"),
        (" ".join(f"{hour:02d}:00/20" for hour in range(11)), "no more than 10"),
    ),
)
async def test_thermostat_schedule_write_validation(
    zigpy_device_from_v2_quirk, schedule, error
):
    """Invalid schedules fail locally and are never sent to the thermostat."""
    cluster = _make_thermostat(zigpy_device_from_v2_quirk)
    cluster.command = mock.AsyncMock()

    with pytest.raises(ValueError, match=error):
        await cluster.write_attributes({"schedule_monday": schedule})

    cluster.command.assert_not_awaited()


def test_thermostat_schedule_response_updates_all_returned_days(
    zigpy_device_from_v2_quirk,
):
    """A standard Get Weekly Schedule response populates local day strings."""
    cluster = _make_thermostat(zigpy_device_from_v2_quirk)
    days = Thermostat.SeqDayOfWeek.Monday | Thermostat.SeqDayOfWeek.Tuesday
    hdr = mock.Mock(
        command_id=Thermostat.ClientCommandDefs.get_weekly_schedule_response.id
    )
    args = Thermostat.ClientCommandDefs.get_weekly_schedule_response.schema(
        num_transitions_for_sequence=2,
        day_of_week_for_sequence=days,
        mode_for_sequence=Thermostat.SeqMode.Heat,
        values=[1080, 1750, 360, 2000],
    )

    cluster.handle_cluster_request(hdr, args)

    expected = "06:00/20 18:00/17.5"
    assert cluster.get("schedule_monday") == expected
    assert cluster.get("schedule_tuesday") == expected
    assert cluster.get("schedule_sunday") is None


@pytest.mark.asyncio
async def test_thermostat_schedule_is_loaded_on_configuration(
    zigpy_device_from_v2_quirk,
):
    """Configuration binds reporting and requests each weekday separately."""
    cluster = _make_thermostat(zigpy_device_from_v2_quirk)
    cluster.bind = mock.AsyncMock()
    cluster.command = mock.AsyncMock()

    await cluster.apply_custom_configuration()

    cluster.bind.assert_awaited_once()
    assert cluster.command.await_args_list == [
        mock.call(
            Thermostat.ServerCommandDefs.get_weekly_schedule.id,
            day,
            Thermostat.SeqMode.Heat,
            expect_reply=False,
        )
        for day in (
            Thermostat.SeqDayOfWeek.Monday,
            Thermostat.SeqDayOfWeek.Tuesday,
            Thermostat.SeqDayOfWeek.Wednesday,
            Thermostat.SeqDayOfWeek.Thursday,
            Thermostat.SeqDayOfWeek.Friday,
            Thermostat.SeqDayOfWeek.Saturday,
            Thermostat.SeqDayOfWeek.Sunday,
        )
    ]


@pytest.mark.asyncio
async def test_thermostat_schedule_read_is_local_and_refreshes_device(
    zigpy_device_from_v2_quirk,
):
    """Manage Zigbee device reads the cache while requesting a fresh schedule."""
    cluster = _make_thermostat(zigpy_device_from_v2_quirk)
    cluster.update_attribute(
        cluster.AttributeDefs.schedule_monday.id,
        "06:00/20 18:00/17.5",
    )
    cluster.command = mock.AsyncMock()

    success, failure = await cluster.read_attributes(["schedule_monday"])

    assert success == {"schedule_monday": "06:00/20 18:00/17.5"}
    assert failure == {}
    cluster.command.assert_awaited_once_with(
        Thermostat.ServerCommandDefs.get_weekly_schedule.id,
        Thermostat.SeqDayOfWeek.Monday,
        Thermostat.SeqMode.Heat,
        expect_reply=False,
    )

    cluster.command.reset_mock()
    assert await cluster.read_attributes(["schedule_monday"], only_cache=True) == (
        {"schedule_monday": "06:00/20 18:00/17.5"},
        {},
    )
    cluster.command.assert_not_awaited()


@pytest.mark.parametrize("model", ("SBDV-00196", "SBDV-00197"))
def test_single_button_actions(zigpy_device_from_v2_quirk, model):
    """A single-button switch emits button_single/double/hold events."""
    device = zigpy_device_from_v2_quirk("SDevices", model)

    cluster = device.endpoints[1].multistate_input
    assert isinstance(cluster, SDevicesButtonCluster)

    listener = mock.MagicMock()
    cluster.add_listener(listener)

    # unknown present_value -> no event
    cluster.update_attribute(PRESENT_VALUE, 5)
    assert listener.zha_send_event.call_count == 0

    for value, action in (
        (1, "button_single"),
        (2, "button_double"),
        (0, "button_hold"),
    ):
        cluster.update_attribute(PRESENT_VALUE, value)
        listener.zha_send_event.assert_called_with(action, {})


@pytest.mark.parametrize("model", ("SBDV-00199", "SBDV-00200"))
@pytest.mark.parametrize("endpoint", (1, 2))
def test_two_button_actions(zigpy_device_from_v2_quirk, model, endpoint):
    """A two-button switch emits per-endpoint {single,double,hold}_switch_N events."""
    device = zigpy_device_from_v2_quirk(
        "SDevices",
        model,
        cluster_ids={
            1: {
                OnOff.cluster_id: ClusterType.Server,
                MultistateInput.cluster_id: ClusterType.Server,
            },
            2: {
                OnOff.cluster_id: ClusterType.Server,
                MultistateInput.cluster_id: ClusterType.Server,
            },
        },
    )

    cluster = device.endpoints[endpoint].multistate_input
    assert isinstance(cluster, SDevicesTwoButtonCluster)

    listener = mock.MagicMock()
    cluster.add_listener(listener)

    cluster.update_attribute(PRESENT_VALUE, 5)
    assert listener.zha_send_event.call_count == 0

    for value, raw in ((1, "single"), (2, "double"), (0, "hold")):
        cluster.update_attribute(PRESENT_VALUE, value)
        listener.zha_send_event.assert_called_with(f"{raw}_switch_{endpoint}", {})


@pytest.mark.parametrize("model", ("SBDV-00199", "SBDV-00200"))
def test_two_button_relays_are_switches(zigpy_device_from_v2_quirk, model):
    """Switch-mode relays get the ON_OFF_OUTPUT device type (switch platform)."""
    device = zigpy_device_from_v2_quirk(
        "SDevices",
        model,
        cluster_ids={
            1: {OnOff.cluster_id: ClusterType.Server},
            2: {OnOff.cluster_id: ClusterType.Server},
        },
    )
    for endpoint in (1, 2):
        assert device.endpoints[endpoint].device_type == zha.DeviceType.ON_OFF_OUTPUT


def test_socket_relay_is_switch(zigpy_device_from_v2_quirk):
    """The socket is a Mains Power Outlet (0x0009) - a switch, not a light."""
    device = zigpy_device_from_v2_quirk("SDevices", "SBDV-00202")
    assert device.endpoints[1].device_type == zha.DeviceType.MAIN_POWER_OUTLET


def test_socket_emergency_flags_split_from_bitmap(zigpy_device_from_v2_quirk):
    """The emergency bitmap is split into per-flag attributes on attribute update."""
    device = zigpy_device_from_v2_quirk("SDevices", "SBDV-00202")
    cluster = device.endpoints[1].sdevices_cluster

    # one flag at a time -> only that flag's synthetic attribute flips
    for attr_name, bitmap in (
        ("emergency_overvoltage", 0x01),
        ("emergency_undervoltage", 0x02),
        ("emergency_overcurrent", 0x04),
        ("emergency_overheat", 0x08),
    ):
        cluster.update_attribute(0x3001, bitmap)
        assert cluster.get(attr_name) is True
        others = {
            "emergency_overvoltage",
            "emergency_undervoltage",
            "emergency_overcurrent",
            "emergency_overheat",
        } - {attr_name}
        assert all(cluster.get(other) is False for other in others)

    # all flags at once -> all set
    cluster.update_attribute(0x3001, 0x0F)
    assert all(
        cluster.get(n) is True
        for n in (
            "emergency_overvoltage",
            "emergency_undervoltage",
            "emergency_overcurrent",
            "emergency_overheat",
        )
    )

    # each flag is its own binary sensor on its synthetic attribute, not the bitmap
    binary_attrs = {
        entity.attribute_name
        for entity in _socket("SDevices", "SBDV-00202").entity_metadata
        if type(entity).__name__ == "BinarySensorMetadata"
    }
    assert binary_attrs == {
        "emergency_overvoltage",
        "emergency_undervoltage",
        "emergency_overcurrent",
        "emergency_overheat",
    }


@pytest.mark.parametrize("model", ("SBDV-00199", "SBDV-00200"))
def test_cover_mode(zigpy_device_from_v2_quirk, model):
    """Covering-mode instance (EP3 WindowCovering) matches the cover quirk."""
    device = zigpy_device_from_v2_quirk(
        "SDevices",
        model,
        endpoint_ids=[3],
        cluster_ids={
            3: {
                WindowCovering.cluster_id: ClusterType.Server,
                Diagnostic.cluster_id: ClusterType.Server,
                SDevicesCluster.cluster_id: ClusterType.Server,
            }
        },
    )

    cluster = device.endpoints[3].window_covering
    assert isinstance(cluster, SDevicesWindowCoveringCluster)
    # manufacturer attribute is available on the replaced cluster
    assert cluster.AttributeDefs.sdevices_calibration_time.id == 0x1001
    # switch-mode gangs must not exist on a covering-mode device
    assert 1 not in device.endpoints
    assert 2 not in device.endpoints


@pytest.mark.asyncio
async def test_button_clusters_bind(zigpy_device_from_v2_quirk):
    """Report sources bind without changing firmware reporting defaults."""
    single = zigpy_device_from_v2_quirk(
        "SDevices",
        "SBDV-00196",
        cluster_ids={
            1: {
                MultistateInput.cluster_id: ClusterType.Server,
                Diagnostic.cluster_id: ClusterType.Server,
            }
        },
    )
    single_cluster = single.endpoints[1].multistate_input
    single_cluster.bind = mock.AsyncMock()
    await single_cluster.apply_custom_configuration()
    single_cluster.bind.assert_awaited_once()

    diagnostic_cluster = single.endpoints[1].diagnostic
    diagnostic_cluster.bind = mock.AsyncMock()
    await diagnostic_cluster.apply_custom_configuration()
    diagnostic_cluster.bind.assert_awaited_once()

    socket = zigpy_device_from_v2_quirk("SDevices", "SBDV-00202")
    socket_reporting_cluster = socket.endpoints[1].sdevices_cluster
    socket_reporting_cluster.bind = mock.AsyncMock()
    await socket_reporting_cluster.apply_custom_configuration()
    socket_reporting_cluster.bind.assert_awaited_once()

    device_temperature_cluster = socket.endpoints[1].device_temperature
    device_temperature_cluster.bind = mock.AsyncMock()
    await device_temperature_cluster.apply_custom_configuration()
    device_temperature_cluster.bind.assert_not_awaited()

    dual = zigpy_device_from_v2_quirk(
        "SDevices",
        "SBDV-00199",
        cluster_ids={
            1: {MultistateInput.cluster_id: ClusterType.Server},
            2: {MultistateInput.cluster_id: ClusterType.Server},
        },
    )
    for endpoint_id in (1, 2):
        dual_cluster = dual.endpoints[endpoint_id].multistate_input
        dual_cluster.bind = mock.AsyncMock()
        await dual_cluster.apply_custom_configuration()
        dual_cluster.bind.assert_awaited_once()


@pytest.mark.asyncio
async def test_manufacturer_cluster_binding_matches_report_sources(
    zigpy_device_from_v2_quirk,
):
    """Bind 0xFCCF only where the reference device emits attribute reports."""
    no_neutral = zigpy_device_from_v2_quirk("SDevices", "SBDV-00196")
    no_neutral_cluster = no_neutral.endpoints[1].sdevices_cluster
    no_neutral_cluster.bind = mock.AsyncMock()
    await no_neutral_cluster.apply_custom_configuration()
    no_neutral_cluster.bind.assert_not_awaited()

    optional_neutral = zigpy_device_from_v2_quirk("SDevices", "SBDV-00197")
    optional_neutral_cluster = optional_neutral.endpoints[1].sdevices_cluster
    optional_neutral_cluster.bind = mock.AsyncMock()
    await optional_neutral_cluster.apply_custom_configuration()
    optional_neutral_cluster.bind.assert_awaited_once()

    dual = zigpy_device_from_v2_quirk(
        "SDevices",
        "SBDV-00199",
        cluster_ids={
            1: {SDevicesCluster.cluster_id: ClusterType.Server},
            2: {SDevicesCluster.cluster_id: ClusterType.Server},
        },
    )
    for endpoint_id, should_bind in ((1, True), (2, False)):
        cluster = dual.endpoints[endpoint_id].sdevices_cluster
        cluster.bind = mock.AsyncMock()
        await cluster.apply_custom_configuration()
        if should_bind:
            cluster.bind.assert_awaited_once()
        else:
            cluster.bind.assert_not_awaited()

    cover = zigpy_device_from_v2_quirk(
        "SDevices",
        "SBDV-00199",
        endpoint_ids=[3],
        cluster_ids={3: {SDevicesCluster.cluster_id: ClusterType.Server}},
    )
    cover_cluster = cover.endpoints[3].sdevices_cluster
    cover_cluster.bind = mock.AsyncMock()
    await cover_cluster.apply_custom_configuration()
    cover_cluster.bind.assert_awaited_once()


@pytest.mark.asyncio
async def test_clusters_retain_firmware_reporting_configuration(
    zigpy_device_from_v2_quirk,
):
    """SDevices clusters acknowledge reporting setup without sending a command."""
    socket = zigpy_device_from_v2_quirk("SDevices", "SBDV-00202")
    clusters_and_attributes = (
        (
            socket.endpoints[1].on_off,
            OnOff.AttributeDefs.on_off,
            SDevicesOnOffCluster,
        ),
        (
            socket.endpoints[1].device_temperature,
            DeviceTemperature.AttributeDefs.current_temperature,
            SDevicesDeviceTemperatureCluster,
        ),
        (
            socket.endpoints[1].sdevices_cluster,
            SDevicesCluster.AttributeDefs.rms_voltage_mv,
            SDevicesCluster,
        ),
    )

    for cluster, attribute, cluster_class in clusters_and_attributes:
        assert isinstance(cluster, cluster_class)
        cluster._configure_reporting = mock.AsyncMock()
        result = await cluster.configure_reporting_multiple(
            {
                attribute: ReportingConfig(
                    min_interval=1,
                    max_interval=2,
                    reportable_change=1,
                )
            }
        )
        assert result == {attribute: foundation.Status.SUCCESS}
        cluster._configure_reporting.assert_not_awaited()

    cover = zigpy_device_from_v2_quirk(
        "SDevices",
        "SBDV-00199",
        endpoint_ids=[3],
        cluster_ids={
            3: {WindowCovering.cluster_id: ClusterType.Server},
        },
    )
    cover_cluster = cover.endpoints[3].window_covering
    cover_cluster._configure_reporting = mock.AsyncMock()
    attribute = WindowCovering.AttributeDefs.current_position_lift_percentage
    result = await cover_cluster.configure_reporting_multiple(
        {
            attribute: ReportingConfig(
                min_interval=1,
                max_interval=2,
                reportable_change=1,
            )
        }
    )
    assert result == {attribute: foundation.Status.SUCCESS}
    cover_cluster._configure_reporting.assert_not_awaited()


def test_device_automation_triggers_use_standard_types():
    """SDevices actions use Home Assistant's localized trigger types/subtypes."""
    single = _single_button_switch("SDevices", "SBDV-00196")
    assert single.device_automation_triggers_metadata == {
        (SHORT_PRESS, BUTTON_1): {COMMAND: "button_single"},
        (DOUBLE_PRESS, BUTTON_1): {COMMAND: "button_double"},
        (LONG_PRESS, BUTTON_1): {COMMAND: "button_hold"},
    }

    dual = _two_button_switch("SDevices", "SBDV-00199")
    assert dual.device_automation_triggers_metadata == {
        (SHORT_PRESS, BUTTON_1): {COMMAND: "single_switch_1"},
        (DOUBLE_PRESS, BUTTON_1): {COMMAND: "double_switch_1"},
        (LONG_PRESS, BUTTON_1): {COMMAND: "hold_switch_1"},
        (SHORT_PRESS, BUTTON_2): {COMMAND: "single_switch_2"},
        (DOUBLE_PRESS, BUTTON_2): {COMMAND: "double_switch_2"},
        (LONG_PRESS, BUTTON_2): {COMMAND: "hold_switch_2"},
    }


@pytest.mark.asyncio
async def test_cover_mode_bit_write_preserves_other_bits(
    zigpy_device_from_v2_quirk,
):
    """Writing one synthetic cover-mode switch preserves every unrelated bit."""
    device = zigpy_device_from_v2_quirk(
        "SDevices",
        "SBDV-00199",
        endpoint_ids=[3],
        cluster_ids={3: {WindowCovering.cluster_id: ClusterType.Server}},
    )
    cluster = device.endpoints[3].window_covering
    mode_attr = WindowCovering.AttributeDefs.window_covering_mode
    initial_mode = (
        WindowCoveringMode.Motor_direction_reversed
        | WindowCoveringMode.LEDs_display_feedback
    )
    cluster.update_attribute(mode_attr.id, initial_mode)

    cluster.write_attributes_raw = mock.AsyncMock(
        return_value=(
            [foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)],
        )
    )
    await cluster.write_attributes({"cover_calibration_mode": True})

    ((written,),), _ = cluster.write_attributes_raw.call_args
    assert written.attrid == mode_attr.id
    assert written.value.value == (
        initial_mode | WindowCoveringMode.Run_in_calibration_mode
    )
    assert cluster.get("cover_calibration_mode") is True
    assert cluster.get("cover_led_feedback") is True


@pytest.mark.asyncio
async def test_cover_mode_bit_write_reads_uncached_mode(
    zigpy_device_from_v2_quirk,
):
    """An uncached Mode is read before clearing a bit and other writes pass through."""
    device = zigpy_device_from_v2_quirk(
        "SDevices",
        "SBDV-00199",
        endpoint_ids=[3],
        cluster_ids={3: {WindowCovering.cluster_id: ClusterType.Server}},
    )
    cluster = device.endpoints[3].window_covering
    mode_attr = WindowCovering.AttributeDefs.window_covering_mode
    initial_mode = (
        WindowCoveringMode.Run_in_calibration_mode
        | WindowCoveringMode.LEDs_display_feedback
    )
    cluster.read_attributes = mock.AsyncMock(
        return_value=({mode_attr.name: initial_mode}, {})
    )
    cluster.write_attributes_raw = mock.AsyncMock(
        return_value=(
            [foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)],
        )
    )

    await cluster.write_attributes(
        {"cover_calibration_mode": False, "velocity_lift": 25}
    )

    cluster.read_attributes.assert_awaited_once()
    ((written),), _ = cluster.write_attributes_raw.call_args
    written_values = {record.attrid: record.value.value for record in written}
    assert written_values == {
        WindowCovering.AttributeDefs.velocity_lift.id: 25,
        mode_attr.id: WindowCoveringMode.LEDs_display_feedback,
    }
    assert cluster.get("cover_calibration_mode") is False
    assert cluster.get("cover_led_feedback") is True


@pytest.mark.asyncio
async def test_cover_mode_bit_write_fails_without_current_mode(
    zigpy_device_from_v2_quirk,
):
    """A synthetic bit cannot be safely written if Mode cannot be read."""
    device = zigpy_device_from_v2_quirk(
        "SDevices",
        "SBDV-00199",
        endpoint_ids=[3],
        cluster_ids={3: {WindowCovering.cluster_id: ClusterType.Server}},
    )
    cluster = device.endpoints[3].window_covering
    cluster.read_attributes = mock.AsyncMock(return_value=({}, {}))
    cluster.write_attributes_raw = mock.AsyncMock()

    with pytest.raises(
        ValueError, match="Unable to read WindowCovering.Mode before updating it"
    ):
        await cluster.write_attributes({"cover_calibration_mode": True})

    cluster.write_attributes_raw.assert_not_awaited()


def test_config_entities_request_initial_values():
    """Writable config entities are read before ZHA checks their support."""
    builders = (
        _single_button_switch("SDevices", "SBDV-00197", optional_neutral=True),
        _two_button_switch("SDevices", "SBDV-00200", optional_neutral=True),
        _socket("SDevices", "SBDV-00202"),
    )
    local_cover_mode_attributes = {
        "cover_calibration_mode",
        "cover_maintenance_mode",
        "cover_led_feedback",
    }

    missing_startup_reads = []
    for builder in builders:
        for metadata in builder.entity_metadata:
            if not isinstance(
                metadata, (NumberMetadata, SwitchMetadata, ZCLEnumMetadata)
            ):
                continue
            if metadata.attribute_name in local_cover_mode_attributes:
                continue
            if (
                metadata.reporting_config is None
                and metadata.attribute_initialized_from_cache
            ):
                missing_startup_reads.append(
                    (metadata.endpoint_id, metadata.attribute_name)
                )

    assert missing_startup_reads == []


def test_optional_neutral_cover_entities_are_declared():
    """SBDV-00200 exposes its optional-neutral attributes on cover endpoint 3."""
    metadata = _two_button_switch(
        "SDevices", "SBDV-00200", optional_neutral=True
    ).entity_metadata
    assert {
        (entity.endpoint_id, entity.attribute_name)
        for entity in metadata
        if entity.attribute_name
        in {"power_profile", "led_indication_type", "neutral_presence"}
    } == {
        (1, "power_profile"),
        (1, "led_indication_type"),
        (1, "neutral_presence"),
        (3, "power_profile"),
        (3, "led_indication_type"),
        (3, "neutral_presence"),
    }
    neutral_entities = [
        entity for entity in metadata if entity.attribute_name == "neutral_presence"
    ]
    assert all(
        entity.attribute_initialized_from_cache is False
        and entity.reporting_config is None
        for entity in neutral_entities
    )


def test_switch_diagnostic_counter_mapping():
    """Diagnostics distinguish pairing and physical wall buttons."""
    single = _single_button_switch("SDevices", "SBDV-00196")
    single_diagnostics = {
        entity.attribute_name
        for entity in single.entity_metadata
        if entity.cluster_id == Diagnostic.cluster_id
    }
    assert {
        "number_of_resets",
        "sdevices_button1_clicks",
        "sdevices_button2_clicks",
        "sdevices_relay1_switches",
    } <= single_diagnostics
    assert "persistent_memory_writes" not in single_diagnostics

    dual = _two_button_switch("SDevices", "SBDV-00199")
    dual_diagnostics = {
        (entity.endpoint_id, entity.attribute_name)
        for entity in dual.entity_metadata
        if entity.cluster_id == Diagnostic.cluster_id
    }
    for endpoint_id in (1, 3):
        assert {
            (endpoint_id, "sdevices_button1_clicks"),
            (endpoint_id, "sdevices_button2_clicks"),
            (endpoint_id, "sdevices_button3_clicks"),
            (endpoint_id, "sdevices_relay1_switches"),
            (endpoint_id, "sdevices_relay2_switches"),
        } <= dual_diagnostics
    assert not any(
        attribute_name == "persistent_memory_writes"
        for _, attribute_name in dual_diagnostics
    )


def test_unsupported_flash_writes_entity_is_not_declared_for_socket():
    """The firmware does not support Diagnostic persistent memory writes."""
    assert not any(
        entity.attribute_name == "persistent_memory_writes"
        for entity in _socket("SDevices", "SBDV-00202").entity_metadata
    )


def test_socket_device_temperature_unique_id_is_preserved():
    """The replacement matches ZHA's native `{ieee}-1-2` unique ID."""
    (metadata,) = (
        entity
        for entity in _socket("SDevices", "SBDV-00202").entity_metadata
        if entity.cluster_id == DeviceTemperature.cluster_id
        and entity.attribute_name == "current_temperature"
    )
    assert metadata.unique_id_suffix == str(DeviceTemperature.cluster_id)


def test_socket_scaling_and_reporting_metadata():
    """Socket declarations leave reporting intervals to the firmware."""
    metadata = _socket("SDevices", "SBDV-00202").entity_metadata
    numbers = {
        entity.attribute_name: entity
        for entity in metadata
        if isinstance(entity, NumberMetadata)
    }
    assert (
        numbers["upper_voltage_threshold"].min,
        numbers["upper_voltage_threshold"].max,
    ) == (230, 260)
    assert numbers["upper_voltage_threshold"].multiplier == 0.001
    assert (
        numbers["lower_voltage_threshold"].min,
        numbers["lower_voltage_threshold"].max,
    ) == (100, 230)
    assert numbers["lower_voltage_threshold"].multiplier == 0.001
    assert (
        numbers["upper_current_threshold"].min,
        numbers["upper_current_threshold"].max,
    ) == (0.1, 16)
    assert numbers["upper_current_threshold"].multiplier == 0.001
    assert (
        numbers["upper_temp_threshold"].min,
        numbers["upper_temp_threshold"].max,
    ) == (10, 100)

    sensors = {
        entity.attribute_name: entity
        for entity in metadata
        if type(entity).__name__ == "ZCLSensorMetadata"
    }
    for attr_name in ("rms_voltage_mv", "rms_current_ma", "active_power_mw"):
        sensor = sensors[attr_name]
        assert sensor.divisor == 1000
        assert sensor.reporting_config is None
        assert sensor.attribute_initialized_from_cache is False

    emergency = sensors["emergency_shutoff_state"]
    assert emergency.initially_disabled is True
    assert emergency.reporting_config is None
    assert emergency.attribute_initialized_from_cache is False


def _make_complete_thermostat(zigpy_device_from_v2_quirk):
    """Create an SBDV-00205 with every cluster replaced by the quirk."""
    return zigpy_device_from_v2_quirk(
        "SDevices",
        "SBDV-00205",
        cluster_ids={
            1: {
                DeviceTemperature.cluster_id: ClusterType.Server,
                Thermostat.cluster_id: ClusterType.Server,
                UserInterface.cluster_id: ClusterType.Server,
                SDevicesCluster.cluster_id: ClusterType.Server,
                Diagnostic.cluster_id: ClusterType.Server,
            }
        },
    )


def test_complete_thermostat_clusters_and_attributes(zigpy_device_from_v2_quirk):
    """The full thermostat quirk augments every relevant device cluster."""
    device = _make_complete_thermostat(zigpy_device_from_v2_quirk)
    thermostat = device.endpoints[1].thermostat

    assert isinstance(thermostat, SDevicesThermostatCluster)
    for attribute_name, attribute_id in (
        ("remote_temperature", 0x4001),
        ("sensor_mode", 0x4003),
        ("heating_hysteresis", 0x4019),
        ("min_local_temperature_limit", 0x40F0),
        ("output_mode", 0x4100),
        ("sensor_error", 0x4102),
        ("event_status", 0x4103),
        ("remote_sensor_timeout", 0x4203),
    ):
        attribute = thermostat.find_attribute(attribute_name)
        assert attribute.id == attribute_id
        assert attribute.manufacturer_code == 0x152F

    assert (
        device.endpoints[1].thermostat_ui.find_attribute("brightness_steady_mode").id
        == 0x2002
    )
    assert device.endpoints[1].device_temperature.__class__.__name__ == (
        "SDevicesDeviceTemperatureCluster"
    )


def test_thermostat_status_bitmaps_are_split(zigpy_device_from_v2_quirk):
    """Emergency, sensor-error and event-status bits update independently."""
    device = _make_complete_thermostat(zigpy_device_from_v2_quirk)
    proprietary = device.endpoints[1].sdevices_cluster
    thermostat = device.endpoints[1].thermostat

    emergency_flags = {
        "emergency_overcurrent": 0x04,
        "emergency_overheat": 0x08,
        "emergency_no_load": 0x10,
        "emergency_no_data": 0x20,
        "emergency_wrong_data": 0x40,
    }
    for attribute_name, bit in emergency_flags.items():
        proprietary.update_attribute(
            SDevicesCluster.AttributeDefs.emergency_shutoff_state.id, bit
        )
        assert proprietary.get(attribute_name) is True
        assert all(
            proprietary.get(other) is False
            for other in emergency_flags
            if other != attribute_name
        )

    for source, flags in (
        (
            SDevicesThermostatCluster.AttributeDefs.sensor_error.id,
            {
                "sensor_error_remote_disconnected": 0x01,
                "sensor_error_local_disconnected": 0x02,
                "sensor_error_short_circuit": 0x04,
            },
        ),
        (
            SDevicesThermostatCluster.AttributeDefs.event_status.id,
            {
                "status_heat_inefficient": 0x01,
                "status_antifrost": 0x02,
                "status_open_window": 0x04,
                "status_invalid_time": 0x08,
            },
        ),
    ):
        for attribute_name, bit in flags.items():
            thermostat.update_attribute(source, bit)
            assert thermostat.get(attribute_name) is True
            assert all(
                thermostat.get(other) is False
                for other in flags
                if other != attribute_name
            )


def test_thermostat_entities_cover_full_feature_set():
    """The builder publishes config, metering, protection and diagnostics."""
    metadata = _thermostat.entity_metadata
    attributes = {
        entity.attribute_name
        for entity in metadata
        if hasattr(entity, "attribute_name")
    }

    assert {
        "sensor_mode",
        "output_mode",
        "local_sensor_type",
        "heating_hysteresis",
        "min_local_temperature_limit",
        "max_local_temperature_limit",
        "remote_temperature_calibration",
        "remote_sensor_timeout",
        "remote_temperature",
        "open_window_enabled",
        "brightness_operations_mode",
        "brightness_steady_mode",
        "brightness_night_mode",
        "rms_voltage_mv",
        "rms_current_ma",
        "active_power_mw",
        "emergency_no_load",
        "sensor_error_remote_disconnected",
        "status_invalid_time",
        "sdevices_uptime_s",
        "sdevices_relay1_switches",
    } <= attributes
    assert "persistent_memory_writes" not in attributes


def test_thermostat_scaling_and_firmware_reporting_defaults():
    """Scaled values retain the reporting table supplied by firmware."""
    metadata = _thermostat.entity_metadata
    numbers = {
        entity.attribute_name: entity
        for entity in metadata
        if isinstance(entity, NumberMetadata)
    }

    assert numbers["remote_temperature_calibration"].multiplier == 0.1
    assert numbers["remote_temperature"].multiplier == 0.01
    assert numbers["remote_temperature"].initially_disabled is True
    assert numbers["upper_current_threshold"].multiplier == 0.001

    remote_entities = [
        entity
        for entity in metadata
        if getattr(entity, "attribute_name", None)
        in {
            "rms_voltage_mv",
            "rms_current_ma",
            "active_power_mw",
            "emergency_shutoff_state",
            "sensor_error",
            "event_status",
            "current_temperature",
        }
    ]
    assert remote_entities
    assert all(entity.reporting_config is None for entity in remote_entities)
    assert all(
        entity.attribute_initialized_from_cache is False for entity in remote_entities
    )


@pytest.mark.asyncio
async def test_thermostat_suppresses_configure_reporting(
    zigpy_device_from_v2_quirk,
):
    """ZHA reporting requests do not overwrite SDevices firmware defaults."""
    cluster = _make_thermostat(zigpy_device_from_v2_quirk)
    cluster._configure_reporting = mock.AsyncMock()
    attribute = Thermostat.AttributeDefs.local_temperature

    result = await cluster.configure_reporting_multiple(
        {
            attribute: ReportingConfig(
                min_interval=1,
                max_interval=2,
                reportable_change=1,
            )
        }
    )

    assert result == {attribute: foundation.Status.SUCCESS}
    cluster._configure_reporting.assert_not_awaited()
