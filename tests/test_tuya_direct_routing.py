"""Tests for direct routing between legacy Tuya clusters."""

from unittest import mock

import pytest
import zigpy.types as t
from zigpy.zcl.clusters.general import (
    AnalogOutput,
    BinaryInput,
    LevelControl,
    OnOff,
    PowerConfiguration,
)
from zigpy.zcl.clusters.hvac import Thermostat, UserInterface

import zhaquirks
from zhaquirks.tuya import (
    ATTR_COVER_DIRECTION,
    ATTR_COVER_INVERTED,
    ATTR_COVER_POSITION,
    TUYA_CMD_BASE,
    TUYA_DP_ID_COVER_INVERTED,
    TUYA_DP_ID_DIRECTION_CHANGE,
    TUYA_DP_ID_PERCENT_STATE,
    TUYA_DP_TYPE_ENUM,
    TUYA_DP_TYPE_VALUE,
    TUYA_GET_DATA,
    TUYA_LEVEL_COMMAND,
    TuyaLevelControl,
    TuyaManufacturerClusterOnOff,
    TuyaManufacturerLevelControl,
    TuyaOnOff,
)
from zhaquirks.tuya.ts0601_cover import (
    TuyaZemismartSmartCover0601,
    TuyaZemismartSmartCover0601_inv_position,
)
from zhaquirks.tuya.ts0601_din_power import (
    HIKING_DIN_SWITCH_ATTR,
    TUYA_DIN_SWITCH_ATTR,
    HikingPowerMeter,
    TuyaPowerMeter,
)
from zhaquirks.tuya.ts0601_electric_heating import (
    MOESBHT_CHILD_LOCK_ATTR,
    MOESBHT_ENABLED_ATTR,
    MOESBHT_MANUAL_MODE_ATTR,
    MOESBHT_RUNNING_MODE_ATTR,
    MOESBHT_SCHEDULE_MODE_ATTR,
    MoesBHT,
)
from zhaquirks.tuya.ts0601_haozee import (
    HAOZEE_AWAY_DAYS_ATTR,
    HAOZEE_AWAY_TEMP_ATTR,
    HAOZEE_CHILD_LOCK_ATTR,
    HAOZEE_CURRENT_MODE_ATTR,
    HAOZEE_CURRENT_ROOM_TEMP_ATTR,
    HAOZEE_ENABLED_ATTR,
    HAOZEE_HEATING_ENABLED_ATTR,
    HAOZEE_MAX_TEMP_LIMIT_ATTR,
    HAOZEE_MIN_TEMP_LIMIT_ATTR,
    HAOZEE_TARGET_TEMP_ATTR,
    HAOZEE_TEMP_CALIBRATION_ATTR,
    HY08WE,
)
from zhaquirks.tuya.ts0601_trv import (
    MOES_BATTERY_LOW_ATTR,
    MOES_CHILD_LOCK_ATTR,
    MOES_WINDOW_DETECT_ATTR,
    SITERWELL_BATTERY_ATTR,
    SITERWELL_CHILD_LOCK_ATTR,
    SITERWELL_VALVE_STATE_ATTR,
    ZONNSMART_BATTERY_ATTR,
    ZONNSMART_BOOST_TIME_ATTR,
    ZONNSMART_CHILD_LOCK_ATTR,
    ZONNSMART_MAX_TEMPERATURE_VAL,
    ZONNSMART_MIN_TEMPERATURE_VAL,
    ZONNSMART_ONLINE_MODE_ENUM_ATTR,
    ZONNSMART_OPENED_WINDOW_TEMP,
    ZONNSMART_TARGET_TEMP_ATTR,
    ZONNSMART_TEMPERATURE_ATTR,
    ZONNSMART_TEMPERATURE_CALIBRATION_ATTR,
    ZONNSMART_WINDOW_DETECT_ATTR,
    MoesHY368_Type1new,
    MoesHY368_Type2,
    SiterwellGS361_Type1,
    SiterwellGS361_Type2,
    ZonnsmartTV01_ZG,
)

zhaquirks.setup()


def test_tuya_din_reports_route_to_exact_on_off_endpoint(
    zigpy_device_from_quirk,
):
    """DIN meter reports must update the intended OnOff endpoint only."""
    tuya_device = zigpy_device_from_quirk(TuyaPowerMeter)
    tuya_device.endpoints[1].tuya_manufacturer.update_attribute(TUYA_DIN_SWITCH_ATTR, 1)
    assert tuya_device.endpoints[1].on_off.get("on_off") == 1

    hiking_device = zigpy_device_from_quirk(HikingPowerMeter)
    hiking_device.endpoints[1].tuya_manufacturer.update_attribute(
        HIKING_DIN_SWITCH_ATTR, 1
    )
    assert hiking_device.endpoints[16].on_off.get("on_off") == 1


async def test_hiking_endpoint_16_command_routes_to_endpoint_1_ef00(
    zigpy_device_from_quirk,
):
    """Synthetic endpoint commands must use the real endpoint 1 EF00 cluster."""
    device = zigpy_device_from_quirk(HikingPowerMeter)
    tuya_cluster = device.endpoints[1].tuya_manufacturer

    with mock.patch.object(tuya_cluster, "tuya_mcu_command") as command_mock:
        await device.endpoints[16].on_off.command(OnOff.ServerCommandDefs.on.id)

    command_mock.assert_called_once()
    payload = command_mock.call_args.args[0]
    assert payload.command_id == TUYA_CMD_BASE + 16
    assert payload.data == [1, OnOff.ServerCommandDefs.on.id]


def test_legacy_level_report_routes_to_level_clusters_without_visiting_zdo(
    device_mock,
):
    """Legacy level reports must fan out only across Zigbee endpoints."""
    endpoint = device_mock.endpoints[1]
    manufacturer_cluster = TuyaManufacturerLevelControl(endpoint)
    level_cluster = TuyaLevelControl(endpoint)
    endpoint.add_input_cluster(manufacturer_cluster.cluster_id, manufacturer_cluster)
    endpoint.add_input_cluster(LevelControl.cluster_id, level_cluster)

    second_endpoint = device_mock.add_endpoint(2)
    second_level_cluster = TuyaLevelControl(second_endpoint)
    second_endpoint.add_input_cluster(LevelControl.cluster_id, second_level_cluster)

    assert 0 in device_mock.endpoints

    payload = mock.Mock(
        status=0,
        tsn=1,
        command_id=TUYA_LEVEL_COMMAND,
        function=0,
        data=[0, 0, 0, 1, 244],
    )
    manufacturer_cluster.handle_cluster_request(
        mock.Mock(command_id=TUYA_GET_DATA), [payload]
    )

    assert level_cluster.get(LevelControl.AttributeDefs.current_level.name) == 127
    assert (
        second_level_cluster.get(LevelControl.AttributeDefs.current_level.name) == 127
    )


@pytest.mark.parametrize(
    "manufacturer_cluster_type",
    (TuyaManufacturerClusterOnOff, TuyaManufacturerLevelControl),
)
def test_legacy_switch_report_routes_to_matching_endpoint(
    device_mock, manufacturer_cluster_type
):
    """Legacy switch reports must update only the endpoint named by the channel."""
    first_endpoint = device_mock.endpoints[1]
    manufacturer_cluster = manufacturer_cluster_type(first_endpoint)
    first_on_off = TuyaOnOff(first_endpoint)
    first_endpoint.add_input_cluster(
        manufacturer_cluster.cluster_id, manufacturer_cluster
    )
    first_endpoint.add_input_cluster(OnOff.cluster_id, first_on_off)

    second_endpoint = device_mock.add_endpoint(2)
    second_on_off = TuyaOnOff(second_endpoint)
    second_endpoint.add_input_cluster(OnOff.cluster_id, second_on_off)

    payload = mock.Mock(
        status=0,
        tsn=1,
        command_id=TUYA_CMD_BASE + second_endpoint.endpoint_id,
        function=0,
        data=[1, 1],
    )
    header = mock.Mock(command_id=TUYA_GET_DATA)
    header.frame_control.disable_default_response = True

    manufacturer_cluster.handle_cluster_request(header, [payload])

    assert first_on_off.get(OnOff.AttributeDefs.on_off.name) is None
    assert second_on_off.get(OnOff.AttributeDefs.on_off.name) == 1


@pytest.mark.parametrize(
    ("attrid", "value", "attribute_name", "expected"),
    (
        (HAOZEE_CURRENT_ROOM_TEMP_ATTR, 215, "local_temperature", 2150),
        (HAOZEE_TARGET_TEMP_ATTR, 205, "occupied_heating_setpoint", 2050),
        (HAOZEE_AWAY_TEMP_ATTR, 17, "unoccupied_heating_setpoint", 1700),
        (
            HAOZEE_TEMP_CALIBRATION_ATTR,
            -3,
            "local_temperature_calibration",
            -30,
        ),
        (HAOZEE_MIN_TEMP_LIMIT_ATTR, 5, "min_heat_setpoint_limit", 500),
        (HAOZEE_MAX_TEMP_LIMIT_ATTR, 30, "max_heat_setpoint_limit", 3000),
        (HAOZEE_AWAY_DAYS_ATTR, 7, "unoccupied_duration_days", 7),
    ),
)
def test_haozee_direct_mapped_reports(
    zigpy_device_from_quirk, attrid, value, attribute_name, expected
):
    """Every Haozee direct mapping must update the thermostat attribute."""
    device = zigpy_device_from_quirk(HY08WE)
    device.endpoints[1].tuya_manufacturer.update_attribute(attrid, value)

    assert device.endpoints[1].thermostat.get(attribute_name) == expected


def test_haozee_state_and_ui_reports(zigpy_device_from_quirk):
    """Haozee state, mode, and lock reports must reach standard clusters."""
    device = zigpy_device_from_quirk(HY08WE)
    source = device.endpoints[1].tuya_manufacturer
    thermostat = device.endpoints[1].thermostat
    ui = device.endpoints[1].thermostat_ui

    source.update_attribute(HAOZEE_ENABLED_ATTR, 1)
    source.update_attribute(HAOZEE_HEATING_ENABLED_ATTR, 1)
    source.update_attribute(HAOZEE_CURRENT_MODE_ATTR, 2)
    source.update_attribute(HAOZEE_CHILD_LOCK_ATTR, 1)

    assert thermostat.get("system_mode") == Thermostat.SystemMode.Heat
    assert thermostat.get("running_state") == Thermostat.RunningState.Heat_State_On
    assert thermostat.get("programing_oper_mode") == (
        Thermostat.ProgrammingOperationMode.Simple
    )
    assert thermostat.get("occupancy") == Thermostat.Occupancy.Unoccupied
    assert ui.get("keypad_lockout") == UserInterface.KeypadLockout.Level_1_lockout


@pytest.mark.parametrize(
    ("first_attr", "first_value", "second_attr", "second_value", "expected_state"),
    (
        (
            ZONNSMART_TEMPERATURE_ATTR,
            200,
            ZONNSMART_TARGET_TEMP_ATTR,
            210,
            Thermostat.RunningState.Heat_State_On,
        ),
        (
            ZONNSMART_TARGET_TEMP_ATTR,
            190,
            ZONNSMART_TEMPERATURE_ATTR,
            200,
            Thermostat.RunningState.Idle,
        ),
    ),
)
def test_zonnsmart_temperature_reports_are_order_independent(
    zigpy_device_from_quirk,
    first_attr,
    first_value,
    second_attr,
    second_value,
    expected_state,
):
    """Either first temperature report must be safe on a cold cache."""
    device = zigpy_device_from_quirk(ZonnsmartTV01_ZG)
    source = device.endpoints[1].tuya_manufacturer
    thermostat = device.endpoints[1].thermostat

    assert thermostat.get("min_heat_setpoint_limit") == ZONNSMART_MIN_TEMPERATURE_VAL
    assert thermostat.get("max_heat_setpoint_limit") == ZONNSMART_MAX_TEMPERATURE_VAL

    source.update_attribute(first_attr, first_value)
    assert thermostat.get("running_state") is None
    source.update_attribute(second_attr, second_value)

    assert thermostat.get("running_state") == expected_state


def test_zonnsmart_reports_route_to_all_declared_endpoints(
    zigpy_device_from_quirk,
):
    """Zonnsmart auxiliary reports must reach their declared clusters."""
    device = zigpy_device_from_quirk(ZonnsmartTV01_ZG)
    source = device.endpoints[1].tuya_manufacturer

    source.update_attribute(ZONNSMART_WINDOW_DETECT_ATTR, 1)
    source.update_attribute(ZONNSMART_OPENED_WINDOW_TEMP, 185)
    source.update_attribute(ZONNSMART_BATTERY_ATTR, 87)
    source.update_attribute(ZONNSMART_TEMPERATURE_CALIBRATION_ATTR, 11)

    assert (
        device.endpoints[1].binary_input.get(
            BinaryInput.AttributeDefs.present_value.name
        )
        == 1
    )
    assert (
        device.endpoints[2].analog_output.get(
            AnalogOutput.AttributeDefs.present_value.name
        )
        == 18.5
    )
    assert (
        device.endpoints[1].power.get(
            PowerConfiguration.AttributeDefs.battery_percentage_remaining.name
        )
        == 174
    )
    assert (
        device.endpoints[1].analog_output.get(
            AnalogOutput.AttributeDefs.present_value.name
        )
        == 1.1
    )


@pytest.mark.parametrize(
    ("attrid", "value", "target_endpoint"),
    (
        (ZONNSMART_BOOST_TIME_ATTR, 60, 1),
        (ZONNSMART_CHILD_LOCK_ATTR, 1, 2),
        (ZONNSMART_ONLINE_MODE_ENUM_ATTR, 1, 3),
    ),
)
def test_zonnsmart_on_off_reports_route_to_exact_endpoint(
    zigpy_device_from_quirk,
    attrid,
    value,
    target_endpoint,
):
    """Each Zonnsmart OnOff report must update only its intended endpoint."""
    device = zigpy_device_from_quirk(ZonnsmartTV01_ZG)

    device.endpoints[1].tuya_manufacturer.update_attribute(attrid, value)

    for endpoint_id in (1, 2, 3):
        expected = 1 if endpoint_id == target_endpoint else None
        assert device.endpoints[endpoint_id].on_off.get("on_off") == expected

    if attrid == ZONNSMART_CHILD_LOCK_ATTR:
        assert device.endpoints[1].thermostat_ui.get("keypad_lockout") == 1


async def test_zonnsmart_cross_endpoint_writes_are_device_isolated(
    zigpy_device_from_quirk,
):
    """Helper writes must use endpoint 1 of their own device."""
    first = zigpy_device_from_quirk(
        ZonnsmartTV01_ZG, ieee=t.EUI64([1, 1, 1, 1, 1, 1, 1, 1])
    )
    second = zigpy_device_from_quirk(
        ZonnsmartTV01_ZG, ieee=t.EUI64([2, 2, 2, 2, 2, 2, 2, 2])
    )
    first_manufacturer = first.endpoints[1].tuya_manufacturer
    second_manufacturer = second.endpoints[1].tuya_manufacturer

    with (
        mock.patch.object(
            first_manufacturer, "write_attributes", new=mock.AsyncMock()
        ) as first_write,
        mock.patch.object(
            second_manufacturer, "write_attributes", new=mock.AsyncMock()
        ) as second_write,
    ):
        await first.endpoints[2].on_off.write_attributes({"on_off": True})
        await first.endpoints[2].analog_output.write_attributes({"present_value": 18.5})

    assert first_write.await_args_list == [
        mock.call({ZONNSMART_CHILD_LOCK_ATTR: t.Bool.true}),
        mock.call({ZONNSMART_OPENED_WINDOW_TEMP: 185.0}),
    ]
    second_write.assert_not_awaited()


@pytest.mark.parametrize("quirk", (SiterwellGS361_Type1, SiterwellGS361_Type2))
def test_siterwell_lock_and_battery_reports(zigpy_device_from_quirk, quirk):
    """Siterwell lock and battery reports must reach UI and power clusters."""
    device = zigpy_device_from_quirk(quirk)
    source = device.endpoints[1].tuya_manufacturer

    source.update_attribute(SITERWELL_CHILD_LOCK_ATTR, 1)
    source.update_attribute(SITERWELL_BATTERY_ATTR, 76)

    assert device.endpoints[1].thermostat_ui.get("keypad_lockout") == 1
    assert device.endpoints[1].power.get("battery_percentage_remaining") == 152


@pytest.mark.parametrize("quirk", (SiterwellGS361_Type1, SiterwellGS361_Type2))
def test_siterwell_valve_state_reports_update_running_state(
    zigpy_device_from_quirk, quirk
):
    """Siterwell valve reports must drive thermostat running mode and state."""
    device = zigpy_device_from_quirk(quirk)
    source = device.endpoints[1].tuya_manufacturer
    thermostat = device.endpoints[1].thermostat

    source.update_attribute(SITERWELL_VALVE_STATE_ATTR, 50)
    assert thermostat.get("running_mode") == Thermostat.RunningMode.Heat
    assert thermostat.get("running_state") == Thermostat.RunningState.Heat_State_On

    source.update_attribute(SITERWELL_VALVE_STATE_ATTR, 0)
    assert thermostat.get("running_mode") == Thermostat.RunningMode.Off
    assert thermostat.get("running_state") == Thermostat.RunningState.Idle


@pytest.mark.parametrize("quirk", (MoesHY368_Type1new, MoesHY368_Type2))
def test_moes_alternate_topologies_route_auxiliary_reports(
    zigpy_device_from_quirk, quirk
):
    """Alternate Moes topologies must retain window, lock, and battery routing."""
    device = zigpy_device_from_quirk(quirk)
    source = device.endpoints[1].tuya_manufacturer

    source.update_attribute(MOES_WINDOW_DETECT_ATTR, [5, 20, 1])
    source.update_attribute(MOES_CHILD_LOCK_ATTR, 1)
    source.update_attribute(MOES_BATTERY_LOW_ATTR, 1)

    assert device.endpoints[1].on_off.get("on_off") == 1
    assert device.endpoints[1].on_off.get("window_detection_temperature") == 2000
    assert device.endpoints[1].on_off.get("window_detection_timeout_minutes") == 5
    assert device.endpoints[1].thermostat_ui.get("keypad_lockout") == 1
    assert device.endpoints[1].power.get("battery_percentage_remaining") == 10


def test_electric_heating_mode_state_and_ui_reports(zigpy_device_from_quirk):
    """Electric heating reports must route to thermostat and UI clusters."""
    device = zigpy_device_from_quirk(MoesBHT)
    source = device.endpoints[1].tuya_manufacturer
    thermostat = device.endpoints[1].thermostat

    source.update_attribute(MOESBHT_SCHEDULE_MODE_ATTR, 0)
    assert thermostat.get("programing_oper_mode") == 1
    source.update_attribute(MOESBHT_MANUAL_MODE_ATTR, 0)
    assert thermostat.get("programing_oper_mode") == 0
    source.update_attribute(MOESBHT_ENABLED_ATTR, 1)
    source.update_attribute(MOESBHT_RUNNING_MODE_ATTR, 0)
    source.update_attribute(MOESBHT_CHILD_LOCK_ATTR, 1)

    assert thermostat.get("system_mode") == Thermostat.SystemMode.Heat
    assert thermostat.get("running_state") == Thermostat.RunningState.Heat_State_On
    assert device.endpoints[1].thermostat_ui.get("keypad_lockout") == 1


@pytest.mark.parametrize(
    ("quirk", "expected_position"),
    (
        (TuyaZemismartSmartCover0601, 75),
        (TuyaZemismartSmartCover0601_inv_position, 25),
    ),
)
def test_legacy_cover_reports_route_to_window_covering(
    zigpy_device_from_quirk, quirk, expected_position
):
    """Legacy cover reports must update the co-resident WindowCovering cluster."""
    device = zigpy_device_from_quirk(quirk)
    source = device.endpoints[1].tuya_manufacturer
    cover = device.endpoints[1].window_covering
    hdr = mock.Mock(command_id=TUYA_GET_DATA)

    position = mock.Mock(
        status=0,
        tsn=1,
        command_id=TUYA_DP_TYPE_VALUE + TUYA_DP_ID_PERCENT_STATE,
        function=0,
        data=[4, 0, 0, 0, 25],
    )
    direction = mock.Mock(
        status=0,
        tsn=2,
        command_id=TUYA_DP_TYPE_ENUM + TUYA_DP_ID_DIRECTION_CHANGE,
        function=0,
        data=[1, 1],
    )
    inverted = mock.Mock(
        status=0,
        tsn=3,
        command_id=TUYA_DP_TYPE_ENUM + TUYA_DP_ID_COVER_INVERTED,
        function=0,
        data=[1, 1],
    )

    for payload in (position, direction, inverted):
        source.handle_cluster_request(hdr, [payload])

    assert cover.get(ATTR_COVER_POSITION) == expected_position
    assert cover.get(ATTR_COVER_DIRECTION) == 1
    assert cover.get(ATTR_COVER_INVERTED) == 1
