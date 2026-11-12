"""Tests for Rti-Tek quirks."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from zha.quirks import DEVICE_REGISTRY
from zigpy.zcl import ClusterType
from zigpy.zcl.clusters.hvac import SeqDayOfWeek, SeqMode, Thermostat
from zigpy.zcl.foundation import Status

import zhaquirks
from zhaquirks.clusters import CustomCluster
from zhaquirks.rti_tek import etrv_zb02
from zhaquirks.rti_tek.etrv_zb02 import (
    ETRV_ZB02_TEMPORARY_MANUAL_TEMPERATURE_ATTR,
    ETRV_ZB02_WEEKLY_SCHEDULE_DAY_ATTR,
    ETRV_ZB02_WEEKLY_SCHEDULE_DISABLED_HOUR,
    ETRV_ZB02_WEEKLY_SCHEDULE_HOUR_ATTRS,
    ETRV_ZB02_WEEKLY_SCHEDULE_MINUTE_ATTRS,
    ETRV_ZB02_WEEKLY_SCHEDULE_NULL_TIME,
    ETRV_ZB02_WEEKLY_SCHEDULE_TEMPERATURE_ATTRS,
    ETRV_ZB02_WEEKLY_SCHEDULE_TIME_ATTRS,
    EtrvZb02ScheduleDay,
    RtiTekEtrvZb02PrivateCluster,
    RtiTekEtrvZb02Thermostat,
    _active_inactive,
    _fault_code_status,
    _today_schedule_day,
    _window_status,
)

zhaquirks.setup()


@pytest.mark.parametrize(
    ("attribute_name", "attribute_id", "type_name", "access"),
    [
        ("child_lock", 0x0001, "Bool", 0x0B),
        ("fault_code", 0x0002, "bitmap32", 0x09),
        ("product_name", 0x0003, "CharacterString", 0x01),
        ("screen_direction", 0x0008, "uint8_t", 0x0B),
        ("screen_display_duration", 0x0009, "uint16_t", 0x0B),
        ("screen_brightness", 0x000A, "uint8_t", 0x0B),
        ("open_window_detection", 0x1000, "Bool", 0x0B),
        ("window_state", 0x1001, "uint8_t", 0x09),
        ("valve_opening", 0x1002, "uint16_t", 0x09),
        ("temperature_control_mode", 0x1004, "EtrvZb02TemperatureControlMode", 0x0B),
        ("valve_switching_difference", 0x1005, "int16s", 0x0B),
        ("frost_protection_enabled", 0x1007, "Bool", 0x0B),
        ("frost_temperature", 0x100A, "int16s", 0x0B),
        ("low_battery_valve_state", 0x1013, "uint8_t", 0x0B),
        ("motor_travel_calibration", 0x1016, "Bool", 0x02),
        ("motor_travel_calibration_status", 0x1017, "uint8_t", 0x09),
        ("holiday_duration", 0x1018, "uint32_t", 0x0B),
        ("boost_duration", 0x1019, "uint32_t", 0x0B),
        ("temporary_manual_mode", 0x101F, "uint8_t", 0x09),
    ],
)
def test_etrv_zb02_private_attribute_definitions(
    attribute_name,
    attribute_id,
    type_name,
    access,
):
    """Each exposed FD22 attribute retains its verified wire contract."""
    attribute = getattr(RtiTekEtrvZb02PrivateCluster.AttributeDefs, attribute_name)

    assert attribute.id == attribute_id
    assert attribute.type.__name__ == type_name
    assert attribute.access.value == access


async def test_etrv_zb02_replaces_private_and_thermostat_clusters(
    zigpy_device_from_v2_quirk,
):
    """The exact Rti-Tek model receives the custom FD22 and Thermostat clusters."""
    device = zigpy_device_from_v2_quirk(
        manufacturer="Rti-Tek",
        model="eTRV-ZB02",
        cluster_ids={
            1: {
                Thermostat.cluster_id: ClusterType.Server,
                RtiTekEtrvZb02PrivateCluster.cluster_id: ClusterType.Server,
            }
        },
    )

    assert isinstance(
        device.endpoints[1].in_clusters[Thermostat.cluster_id],
        RtiTekEtrvZb02Thermostat,
    )
    assert isinstance(
        device.endpoints[1].in_clusters[RtiTekEtrvZb02PrivateCluster.cluster_id],
        RtiTekEtrvZb02PrivateCluster,
    )


async def test_etrv_zb02_private_attribute_contract(
    zigpy_device_from_v2_quirk,
):
    """FD22 uses the documented IDs, raw types, and full-report command."""
    device = zigpy_device_from_v2_quirk(
        manufacturer="Rti-Tek",
        model="eTRV-ZB02",
        cluster_ids={1: {RtiTekEtrvZb02PrivateCluster.cluster_id: ClusterType.Server}},
    )
    cluster = device.endpoints[1].rti_tek_etrv_zb02_private

    assert cluster.AttributeDefs.frost_temperature.id == 0x100A
    assert cluster.AttributeDefs.frost_temperature.type.__name__ == "int16s"
    assert cluster.AttributeDefs.boost_duration.id == 0x1019
    assert cluster.AttributeDefs.boost_duration.type.__name__ == "uint32_t"
    assert cluster.ServerCommandDefs.request_all_attributes.id == 0x00


async def test_etrv_zb02_registers_entities_without_a_full_report_button(
    zigpy_device_from_v2_quirk,
):
    """The internal synchronization command is deliberately not user-facing."""
    device = zigpy_device_from_v2_quirk(
        manufacturer="Rti-Tek",
        model="eTRV-ZB02",
        cluster_ids={
            1: {
                Thermostat.cluster_id: ClusterType.Server,
                RtiTekEtrvZb02PrivateCluster.cluster_id: ClusterType.Server,
            }
        },
    )
    entry = DEVICE_REGISTRY.match_entry(device)
    assert entry is not None
    attributes = {
        metadata.attribute_name
        for metadata in entry.zha_device_factory.quirk_definition.entity_metadata
        if hasattr(metadata, "attribute_name")
    }

    assert {
        "child_lock",
        "frost_temperature",
        "boost_duration",
        "holiday_duration",
        "temporary_manual_mode",
        "weekly_schedule_day",
        "weekly_schedule_period_12_temperature",
    } <= attributes
    assert "request_all_attributes" not in attributes


async def test_etrv_zb02_requests_a_full_report_once_for_missing_report_values(
    zigpy_device_from_v2_quirk,
):
    """A missing device-reported value yields one FD22 full-report command."""
    device = zigpy_device_from_v2_quirk(
        manufacturer="Rti-Tek",
        model="eTRV-ZB02",
        cluster_ids={1: {RtiTekEtrvZb02PrivateCluster.cluster_id: ClusterType.Server}},
    )
    cluster = device.endpoints[1].rti_tek_etrv_zb02_private
    cluster.request_all_attributes = AsyncMock()

    assert await cluster.request_reported_attributes_if_needed() is True
    cluster.request_all_attributes.assert_awaited_once_with(expect_reply=False)
    assert await cluster.request_reported_attributes_if_needed() is True
    cluster.request_all_attributes.assert_awaited_once()


async def test_etrv_zb02_allows_retry_when_the_full_report_request_fails(
    zigpy_device_from_v2_quirk,
):
    """A failed send does not consume the initialization cycle's one request."""
    device = zigpy_device_from_v2_quirk(
        manufacturer="Rti-Tek",
        model="eTRV-ZB02",
        cluster_ids={1: {RtiTekEtrvZb02PrivateCluster.cluster_id: ClusterType.Server}},
    )
    cluster = device.endpoints[1].rti_tek_etrv_zb02_private
    cluster.request_all_attributes = AsyncMock(side_effect=RuntimeError("no route"))

    with pytest.raises(RuntimeError, match="no route"):
        await cluster.request_reported_attributes_if_needed()

    cluster.request_all_attributes = AsyncMock()
    assert await cluster.request_reported_attributes_if_needed() is True
    cluster.request_all_attributes.assert_awaited_once_with(expect_reply=False)


async def test_etrv_zb02_builds_a_twelve_transition_heating_schedule(
    zigpy_device_from_v2_quirk,
):
    """Disabled editor rows are padded for the device's 12-transition command."""
    device = zigpy_device_from_v2_quirk(
        manufacturer="Rti-Tek",
        model="eTRV-ZB02",
        cluster_ids={1: {Thermostat.cluster_id: ClusterType.Server}},
    )
    cluster = device.endpoints[1].thermostat
    cluster.update_attribute(ETRV_ZB02_WEEKLY_SCHEDULE_TIME_ATTRS[1], 360)
    cluster.update_attribute(ETRV_ZB02_WEEKLY_SCHEDULE_TEMPERATURE_ATTRS[1], 2000)
    cluster.update_attribute(ETRV_ZB02_WEEKLY_SCHEDULE_TIME_ATTRS[2], 1320)
    cluster.update_attribute(ETRV_ZB02_WEEKLY_SCHEDULE_TEMPERATURE_ATTRS[2], 1800)

    _day, transitions, values = cluster.build_weekly_schedule()

    assert isinstance(cluster, RtiTekEtrvZb02Thermostat)
    assert len(transitions) == 12
    assert transitions[:2] == [(360, 2000), (1320, 1800)]
    assert transitions[-1] == (1320, 1800)
    assert len(values) == 24


@pytest.mark.parametrize(
    ("value", "fault", "active", "window"),
    [
        (0, "No error", "Inactive", "Not detected"),
        (
            0b1010,
            "Motor operation fault, Low battery blocks firmware upgrade",
            "Active",
            "Detected",
        ),
        (0x10, "Unknown error (0x00000010)", "Active", "Detected"),
        (None, "Unknown error", "Unknown", "Unknown"),
    ],
)
def test_etrv_zb02_status_converters(value, fault, active, window):
    """Reported FD22 states retain their UI-safe status strings."""
    assert _fault_code_status(value) == fault
    assert _active_inactive(value) == active
    assert _window_status(value) == window


def test_etrv_zb02_today_schedule_day_uses_standard_weekday_bits():
    """The initial daily read uses one valid Thermostat weekday bit."""
    assert _today_schedule_day(None) in {
        int(member.value) for member in EtrvZb02ScheduleDay
    }


async def test_etrv_zb02_schedule_editor_validates_and_adjusts_same_hour(
    zigpy_device_from_v2_quirk,
):
    """Schedule hour edits keep periods ordered within the same hour."""
    device = zigpy_device_from_v2_quirk(
        manufacturer="Rti-Tek",
        model="eTRV-ZB02",
        cluster_ids={1: {Thermostat.cluster_id: ClusterType.Server}},
    )
    cluster = device.endpoints[1].thermostat

    assert cluster._period_index(ETRV_ZB02_WEEKLY_SCHEDULE_TIME_ATTRS[1]) == 1
    assert cluster._period_index(0xFFFF) is None

    await cluster.write_attributes(
        {ETRV_ZB02_WEEKLY_SCHEDULE_TEMPERATURE_ATTRS[1]: 2000}
    )
    await cluster.write_attributes({ETRV_ZB02_WEEKLY_SCHEDULE_TIME_ATTRS[1]: 360})
    await cluster.write_attributes(
        {ETRV_ZB02_WEEKLY_SCHEDULE_TEMPERATURE_ATTRS[2]: 2000}
    )
    await cluster.write_attributes({ETRV_ZB02_WEEKLY_SCHEDULE_HOUR_ATTRS[2]: 6})

    assert cluster._editor_value(ETRV_ZB02_WEEKLY_SCHEDULE_TIME_ATTRS[2]) == 361
    assert cluster._editor_value(ETRV_ZB02_WEEKLY_SCHEDULE_MINUTE_ATTRS[2]) == 1

    await cluster.write_attributes(
        {
            ETRV_ZB02_WEEKLY_SCHEDULE_HOUR_ATTRS[
                2
            ]: ETRV_ZB02_WEEKLY_SCHEDULE_DISABLED_HOUR
        }
    )
    assert (
        cluster._editor_value(ETRV_ZB02_WEEKLY_SCHEDULE_TIME_ATTRS[2])
        == ETRV_ZB02_WEEKLY_SCHEDULE_NULL_TIME
    )

    with pytest.raises(ValueError, match="disabled"):
        await cluster.write_attributes({ETRV_ZB02_WEEKLY_SCHEDULE_MINUTE_ATTRS[2]: 1})
    with pytest.raises(ValueError, match="0-23"):
        await cluster.write_attributes({ETRV_ZB02_WEEKLY_SCHEDULE_HOUR_ATTRS[2]: 24})
    with pytest.raises(ValueError, match="0-59"):
        await cluster.write_attributes({ETRV_ZB02_WEEKLY_SCHEDULE_MINUTE_ATTRS[1]: 60})


@pytest.mark.parametrize(
    "periods, message",
    [
        ([(24 * 60, 2000)], "00:00 and 23:59"),
        ([(360, 2000), (360, 2100)], "strictly increasing"),
        ([(360, 400)], "between 5 and 30 C"),
    ],
)
def test_etrv_zb02_schedule_rejects_invalid_transitions(periods, message):
    """The standard schedule payload cannot contain invalid transitions."""
    with pytest.raises(ValueError, match=message):
        RtiTekEtrvZb02Thermostat._validate_periods(periods)


async def test_etrv_zb02_schedule_response_fetch_and_apply(
    monkeypatch,
    zigpy_device_from_v2_quirk,
):
    """Standard Get/Set Weekly Schedule commands update the local editor."""
    device = zigpy_device_from_v2_quirk(
        manufacturer="Rti-Tek",
        model="eTRV-ZB02",
        cluster_ids={1: {Thermostat.cluster_id: ClusterType.Server}},
    )
    cluster = device.endpoints[1].thermostat
    response = (
        3,
        int(SeqDayOfWeek.Monday),
        int(SeqMode.Heat),
        [360, 2000, 720, 1800, 720, 1800],
    )

    assert cluster._store_schedule_response(response)
    assert cluster._weekly_schedule_cache[int(SeqDayOfWeek.Monday)] == [
        (360, 2000),
        (720, 1800),
    ]
    assert not cluster._store_schedule_response((0, 0, 0, []))
    assert not cluster._store_schedule_response((1, 1, int(SeqMode.Heat), [1440, 2000]))
    assert not cluster._store_schedule_response((1, 1))
    assert not cluster._store_schedule_response(
        ("bad", 1, int(SeqMode.Heat), [0, 2000])
    )
    assert not cluster._store_schedule_response((1, 1, 0, [0, 2000]))
    assert not cluster._store_schedule_response(
        (2, 1, int(SeqMode.Heat), [360, 2000, 180, 2000])
    )

    object_response = SimpleNamespace(
        num_transitions_for_sequence=1,
        day_of_week_for_sequence=int(SeqDayOfWeek.Tuesday),
        mode_for_sequence=int(SeqMode.Heat),
        values=[480, 2100],
    )
    assert cluster._store_schedule_response([object_response])
    assert cluster._weekly_schedule_cache[int(SeqDayOfWeek.Tuesday)] == [(480, 2100)]

    cluster.get_weekly_schedule = AsyncMock(return_value=response)
    assert (
        await cluster.schedule_fetch(
            expect_reply=False, days_to_return=int(SeqDayOfWeek.Monday)
        )
        == response
    )
    cluster.get_weekly_schedule.assert_awaited_once_with(
        days_to_return=SeqDayOfWeek.Monday,
        mode_to_return=SeqMode.Heat,
        expect_reply=False,
    )

    cluster.set_weekly_schedule = AsyncMock(
        return_value=SimpleNamespace(status=Status.SUCCESS)
    )
    cluster.schedule_fetch = AsyncMock()
    monkeypatch.setattr(etrv_zb02.asyncio, "sleep", AsyncMock())
    await cluster.schedule_apply()
    cluster.set_weekly_schedule.assert_awaited_once()
    cluster.schedule_fetch.assert_awaited_once_with(
        days_to_return=int(SeqDayOfWeek.Monday)
    )

    cluster.set_weekly_schedule = AsyncMock(
        return_value=SimpleNamespace(status=Status.FAILURE)
    )
    with pytest.raises(ValueError, match="apply failed"):
        await cluster.schedule_apply()

    assert (
        cluster.handle_cluster_request(SimpleNamespace(command_id=0), response) is None
    )


async def test_etrv_zb02_schedule_local_reads_and_temporary_temperature(
    monkeypatch,
    zigpy_device_from_v2_quirk,
):
    """Editor fields remain local while temporary temperature writes reach Thermostat."""
    device = zigpy_device_from_v2_quirk(
        manufacturer="Rti-Tek",
        model="eTRV-ZB02",
        cluster_ids={1: {Thermostat.cluster_id: ClusterType.Server}},
    )
    cluster = device.endpoints[1].thermostat
    base_read = AsyncMock(
        side_effect=[
            ({"editor": 1}, {}),
            ({"device": 2}, {}),
            ({"unknown": 3}, {}),
        ]
    )
    monkeypatch.setattr(CustomCluster, "read_attributes", base_read)

    success, failure = await cluster.read_attributes(
        [
            ETRV_ZB02_WEEKLY_SCHEDULE_TIME_ATTRS[1],
            Thermostat.AttributeDefs.occupied_heating_setpoint.name,
        ]
    )

    assert success == {"editor": 1, "device": 2}
    assert failure == {}
    assert base_read.await_count == 2

    success, failure = await cluster.read_attributes(["not_an_attribute"])
    assert success == {"unknown": 3}
    assert failure == {}

    base_write = AsyncMock(return_value=({}, {}))
    monkeypatch.setattr(CustomCluster, "write_attributes", base_write)
    await cluster.write_attributes({ETRV_ZB02_TEMPORARY_MANUAL_TEMPERATURE_ATTR: 2050})
    assert cluster._attr_cache[ETRV_ZB02_TEMPORARY_MANUAL_TEMPERATURE_ATTR] == 2050
    with pytest.raises(ValueError, match="0.5 C steps"):
        await cluster.write_attributes(
            {ETRV_ZB02_TEMPORARY_MANUAL_TEMPERATURE_ATTR: 2051}
        )
    with pytest.raises(ValueError, match="between 5 and 30 C"):
        await cluster.write_attributes(
            {ETRV_ZB02_TEMPORARY_MANUAL_TEMPERATURE_ATTR: 400}
        )


async def test_etrv_zb02_schedule_editor_day_temperature_and_limits(
    zigpy_device_from_v2_quirk,
):
    """The local schedule editor validates day, temperatures, and ordering limits."""
    device = zigpy_device_from_v2_quirk(
        manufacturer="Rti-Tek",
        model="eTRV-ZB02",
        cluster_ids={1: {Thermostat.cluster_id: ClusterType.Server}},
    )
    cluster = device.endpoints[1].thermostat

    with pytest.raises(ValueError, match="one weekday"):
        await cluster.write_attributes({ETRV_ZB02_WEEKLY_SCHEDULE_DAY_ATTR: 3})
    with pytest.raises(ValueError, match="needs at least one period"):
        cluster.build_weekly_schedule()

    await cluster.write_attributes(
        {ETRV_ZB02_WEEKLY_SCHEDULE_TEMPERATURE_ATTRS[1]: 2000}
    )
    await cluster.write_attributes({ETRV_ZB02_WEEKLY_SCHEDULE_TIME_ATTRS[1]: 1439})
    with pytest.raises(ValueError, match="No later weekly schedule minute"):
        await cluster.write_attributes({ETRV_ZB02_WEEKLY_SCHEDULE_HOUR_ATTRS[2]: 23})
    with pytest.raises(ValueError, match="between 5 and 30 C"):
        await cluster.write_attributes(
            {ETRV_ZB02_WEEKLY_SCHEDULE_TEMPERATURE_ATTRS[1]: 400}
        )
    with pytest.raises(ValueError, match="between 00:00 and 23:59"):
        cluster._set_period_time(1, 1440)

    cluster._weekly_schedule_cache[int(SeqDayOfWeek.Tuesday)] = [(480, 2100)]
    await cluster.write_attributes(
        {ETRV_ZB02_WEEKLY_SCHEDULE_DAY_ATTR: int(SeqDayOfWeek.Tuesday)}
    )
    assert cluster._editor_value(ETRV_ZB02_WEEKLY_SCHEDULE_TIME_ATTRS[1]) == 480


async def test_etrv_zb02_schedule_local_edge_paths(
    monkeypatch,
    zigpy_device_from_v2_quirk,
):
    """Local schedule operations preserve standard Thermostat behavior elsewhere."""
    device = zigpy_device_from_v2_quirk(
        manufacturer="Rti-Tek",
        model="eTRV-ZB02",
        cluster_ids={1: {Thermostat.cluster_id: ClusterType.Server}},
    )
    cluster = device.endpoints[1].thermostat

    cluster._attr_cache[ETRV_ZB02_WEEKLY_SCHEDULE_DAY_ATTR] = 3
    with pytest.raises(ValueError, match="one weekday"):
        cluster.build_weekly_schedule()
    assert not cluster._store_schedule_response(None)

    parent_request = Mock(return_value="parent result")
    monkeypatch.setattr(Thermostat, "handle_cluster_request", parent_request)
    assert (
        cluster.handle_cluster_request(SimpleNamespace(command_id=1), ())
        == "parent result"
    )

    cluster._update_attribute(
        Thermostat.AttributeDefs.occupied_heating_setpoint.id, 2050
    )
    assert cluster._attr_cache[ETRV_ZB02_TEMPORARY_MANUAL_TEMPERATURE_ATTR] == 2050

    base_read = AsyncMock(return_value=({"editor": 1}, {}))
    monkeypatch.setattr(CustomCluster, "read_attributes", base_read)
    assert await cluster.read_attributes([ETRV_ZB02_WEEKLY_SCHEDULE_TIME_ATTRS[1]]) == (
        {"editor": 1},
        {},
    )

    base_write = AsyncMock(return_value=({}, {}))
    monkeypatch.setattr(CustomCluster, "write_attributes", base_write)
    await cluster.write_attributes({"not_an_attribute": 1})
    base_write.assert_awaited_once_with({"not_an_attribute": 1})

    cluster._period_index = Mock(return_value=None)
    await cluster.write_attributes({ETRV_ZB02_WEEKLY_SCHEDULE_TIME_ATTRS[1]: 360})

    del cluster._period_index
    cluster._attr_cache[ETRV_ZB02_WEEKLY_SCHEDULE_TIME_ATTRS[1]] = 360
    cluster._attr_cache[ETRV_ZB02_WEEKLY_SCHEDULE_HOUR_ATTRS[1]] = 6
    cluster._attr_cache[ETRV_ZB02_WEEKLY_SCHEDULE_TEMPERATURE_ATTRS[1]] = 2000
    await cluster.write_attributes({ETRV_ZB02_WEEKLY_SCHEDULE_MINUTE_ATTRS[1]: 1})
    assert cluster._editor_value(ETRV_ZB02_WEEKLY_SCHEDULE_TIME_ATTRS[1]) == 361


async def test_etrv_zb02_private_cache_reading_and_boost_rounding(
    monkeypatch,
    zigpy_device_from_v2_quirk,
):
    """FD22 reports use cache while Boost values are rounded down to full minutes."""
    device = zigpy_device_from_v2_quirk(
        manufacturer="Rti-Tek",
        model="eTRV-ZB02",
        cluster_ids={1: {RtiTekEtrvZb02PrivateCluster.cluster_id: ClusterType.Server}},
    )
    cluster = device.endpoints[1].rti_tek_etrv_zb02_private
    base_read = AsyncMock(
        side_effect=[
            ({"cached": 1}, {}),
            ({"ordinary": 2}, {}),
            ({}, {}),
            ({"unknown": 3}, {}),
        ]
    )
    monkeypatch.setattr(CustomCluster, "read_attributes", base_read)

    success, failure = await cluster.read_attributes(
        ["child_lock", "product_name"], allow_cache=True
    )

    assert success == {"cached": 1, "ordinary": 2}
    assert failure == {}
    assert base_read.await_count == 2
    assert base_read.await_args_list[0].kwargs == {
        "allow_cache": True,
        "only_cache": True,
    }

    await cluster.read_attributes([], allow_cache=False)
    await cluster.read_attributes(["not_an_attribute"], allow_cache=True)
    assert base_read.await_count == 4

    base_read = AsyncMock(return_value=({"cached": 1}, {}))
    monkeypatch.setattr(CustomCluster, "read_attributes", base_read)
    assert await cluster.read_attributes(["child_lock"], allow_cache=True) == (
        {"cached": 1},
        {},
    )

    base_write = AsyncMock(return_value=({}, {}))
    monkeypatch.setattr(CustomCluster, "write_attributes", base_write)
    await cluster.write_attributes({"boost_duration": 125, 0x1019: -1})
    assert base_write.await_args.args[0] == {"boost_duration": 120, 0x1019: 0}

    for attrid in cluster.report_attribute_ids:
        cluster._attr_cache[attrid] = 1
    assert not await cluster.request_reported_attributes_if_needed()
    cluster._report_request_sent = True
    cluster.reset_report_request_cycle()
    assert not cluster._report_request_sent
