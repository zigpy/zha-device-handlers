"""Tests for the Sonoff TRV-ZBT quirk."""

from unittest import mock

import pytest
from zigpy.zcl import ClusterType, foundation
from zigpy.zcl.clusters.general import Basic
from zigpy.zcl.clusters.hvac import Thermostat

import zhaquirks
from zhaquirks.sonoff import trv_zbt
from zhaquirks.sonoff.trv_zbt import (
    CustomSonoffCluster,
    SonoffScheduleGroupCommand,
    SonoffThermostat,
    convert_sonoff_trvzbt_fault_code,
    convert_sonoff_trvzbt_open_window_detected,
    parse_sonoff_trvzbt_schedule_group,
)

zhaquirks.setup()


async def test_trv_zbt_matches_exact_model(zigpy_device_from_v2_quirk):
    """The FC11 and thermostat clusters are replaced for TRV-ZBT only."""

    device = zigpy_device_from_v2_quirk(
        manufacturer="SONOFF",
        model="TRV-ZBT",
        cluster_ids={
            1: {
                Basic.cluster_id: ClusterType.Server,
                Thermostat.cluster_id: ClusterType.Server,
                CustomSonoffCluster.cluster_id: ClusterType.Server,
            }
        },
    )

    assert isinstance(
        device.endpoints[1].in_clusters[CustomSonoffCluster.cluster_id],
        CustomSonoffCluster,
    )
    assert isinstance(
        device.endpoints[1].in_clusters[Thermostat.cluster_id],
        SonoffThermostat,
    )


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (0, "Normal"),
        (0x0A020005, "Temperature sensor issue, Low battery"),
        (0x0A020040, "Unknown"),
    ],
)
def test_trv_zbt_fault_code_decoding(value, expected):
    """Packed fault bitmaps are converted into useful diagnostic text."""

    assert convert_sonoff_trvzbt_fault_code(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (b"\x20\x03\x00\x00\x01\x01", "Detected"),
        (b"\x20\x03\x00\x00\x01\x00", "Not detected"),
        (b"", "Not detected"),
        (b"\x01\x02", None),
    ],
)
def test_trv_zbt_open_window_notification_decoding(value, expected):
    """FC11 HVAC notifications distinguish open-window states."""

    assert convert_sonoff_trvzbt_open_window_detected(value) == expected


def test_trv_zbt_schedule_group_decoding():
    """A variable-length schedule response decodes its transitions correctly."""

    schedule = parse_sonoff_trvzbt_schedule_group(
        b"\x01\x00\x00\x02\x02\x01\x00\x00\x40\x06\x90\x01\x08\x07"
    )

    assert schedule is not None
    assert schedule["day_name"] == "Monday"
    assert schedule["schedule"] == "00:00/16 06:40/18"


def test_trv_zbt_schedule_group_command_serialization():
    """Schedule reads and writes use the device's variable-length payload."""

    read_command = SonoffScheduleGroupCommand(1, 0, 2)
    write_command = SonoffScheduleGroupCommand(
        1,
        1,
        2,
        transition_count=2,
        day_of_week=0x02,
        mode=1,
        transition_1_time=0,
        transition_1_heat_setpoint=1600,
        transition_2_time=400,
        transition_2_heat_setpoint=1800,
    )

    assert read_command.serialize() == b"\x01\x00\x02"
    assert write_command.serialize() == (
        b"\x01\x01\x02\x02\x02\x01\x00\x00\x40\x06\x90\x01\x08\x07"
    )


async def test_trv_zbt_schedule_and_bluetooth_responses_update_virtual_state(
    zigpy_device_from_v2_quirk,
):
    """Private device responses update their corresponding HA-facing state."""

    device = zigpy_device_from_v2_quirk(
        "SONOFF",
        "TRV-ZBT",
        cluster_ids={1: {CustomSonoffCluster.cluster_id: ClusterType.Server}},
    )
    cluster = device.endpoints[1].in_clusters[CustomSonoffCluster.cluster_id]
    header = foundation.ZCLHeader()

    with (
        mock.patch.object(cluster, "_sonoff_trvzbt_schedule_temporary_mode_read"),
        mock.patch.object(cluster, "_sonoff_trvzbt_schedule_device_work_mode_read"),
    ):
        header.command_id = 0x13
        cluster.handle_cluster_request(
            header,
            [b"\x01\x00\x00\x01\x02\x01\x00\x00\x40\x06"],
        )
        header.command_id = 0x10
        cluster.handle_cluster_request(header, [b"\x01\x00"])

    assert (
        cluster._attr_cache[cluster.AttributeDefs.weekly_schedule_monday.id]
        == "00:00/16"
    )
    assert (
        cluster._attr_cache[cluster.AttributeDefs.bluetooth_pairing_status.id]
        == "success"
    )


def test_trv_zbt_protocol_helper_edge_cases():
    """Protocol helpers validate malformed values and preserve raw payloads."""

    command = SonoffScheduleGroupCommand(
        1,
        1,
        2,
        transition_count=1,
        day_of_week=2,
        mode=1,
        transition_1_time=0,
        transition_1_heat_setpoint=1600,
    )
    assert "transition_1_time=0" in repr(command)

    with pytest.raises(ValueError, match="Unsupported"):
        SonoffScheduleGroupCommand(1, 2, 0).serialize()
    with pytest.raises(ValueError, match="transition_count"):
        SonoffScheduleGroupCommand(1, 1, 0).serialize()
    with pytest.raises(ValueError, match="uint8"):
        SonoffScheduleGroupCommand(256, 0, 0).serialize()
    with pytest.raises(ValueError, match="uint16"):
        SonoffScheduleGroupCommand._uint16_le(65536, "time")
    with pytest.raises(ValueError, match="int16"):
        SonoffScheduleGroupCommand._int16_le(32768, "temperature")

    assert trv_zbt.SonoffRawBytes(b"\x01\x02").serialize() == b"\x01\x02"
    assert trv_zbt.SonoffRawBytes.deserialize(b"\x01")[1] == b""

    class ValueContainer:
        value = (1, 2, 3)

    class ValuesContainer:
        values = (4, 5, 6)

    assert trv_zbt.SonoffHvacMessageNotification(None) == b""
    assert trv_zbt.SonoffHvacMessageNotification(bytearray(b"\x01")) == b"\x01"
    assert trv_zbt.SonoffHvacMessageNotification(ValueContainer()) == b"\x01\x02\x03"
    assert trv_zbt.SonoffHvacMessageNotification(ValuesContainer()) == b"\x04\x05\x06"
    assert trv_zbt.SonoffHvacMessageNotification(1) == b""
    assert trv_zbt.SonoffHvacMessageNotification.deserialize(b"\x07")[0] == b"\x07"

    assert trv_zbt.convert_sonoff_trvzbt_fault_code(None) == "Unknown"
    assert trv_zbt.convert_sonoff_trvzbt_fault_code(-1) == "Unknown"
    assert trv_zbt.convert_sonoff_trvzbt_fault_code(0x100000000) == "Unknown"
    assert trv_zbt.convert_sonoff_trvzbt_fault_code(0x80) == "Unknown"
    assert (
        trv_zbt.convert_sonoff_trvzbt_motor_travel_calibration_status(None) == "Unknown"
    )
    assert trv_zbt.convert_sonoff_trvzbt_motor_travel_calibration_status(0) == "Normal"
    assert (
        trv_zbt.convert_sonoff_trvzbt_motor_travel_calibration_status(2)
        == "Unknown 0x02"
    )
    assert trv_zbt.convert_sonoff_trvzbt_device_work_mode(None) == "Unknown"
    assert trv_zbt.convert_sonoff_trvzbt_device_work_mode(3) == "Manual"
    assert trv_zbt.convert_sonoff_trvzbt_device_work_mode(8) == "Unknown 0x08"
    assert trv_zbt.convert_sonoff_trvzbt_open_window_detected(None) is None
    assert trv_zbt.convert_sonoff_trvzbt_open_window_detected(1) is None
    assert trv_zbt.convert_sonoff_trvzbt_weekly_program_state(None) == "unknown"
    assert trv_zbt.convert_sonoff_trvzbt_weekly_program_state(0) == "none"
    assert trv_zbt.convert_sonoff_trvzbt_weekly_program_state(0x81) == "Monday, unknown"
    assert trv_zbt._sonoff_trvzbt_bytes([b"\x01"]) == b"\x01"
    assert trv_zbt._sonoff_trvzbt_bytes(None) == b""

    write_response = trv_zbt.parse_sonoff_trvzbt_schedule_group(b"\x01\x01\x02\x00")
    assert write_response["response_type"] == "write"
    assert write_response["status_name"] == "success"
    assert trv_zbt.parse_sonoff_trvzbt_schedule_group(b"\x01") is None
    assert (
        trv_zbt.parse_sonoff_trvzbt_schedule_group(b"\x01\x00\x00\x01\x02\x01") is None
    )


async def test_trv_zbt_schedule_editor_helpers(zigpy_device_from_v2_quirk):
    """The editor cache produces protocol payloads and restores read schedules."""

    device = zigpy_device_from_v2_quirk(
        "SONOFF",
        "TRV-ZBT",
        cluster_ids={1: {CustomSonoffCluster.cluster_id: ClusterType.Server}},
    )
    cluster = device.endpoints[1].in_clusters[CustomSonoffCluster.cluster_id]
    payload, group, day, transitions = trv_zbt._sonoff_trvzbt_build_editor_payload(
        cluster
    )

    assert payload[:3] == b"\x01\x01\x00"
    assert group == 0
    assert day in trv_zbt.SONOFF_TRVZBT_SCHEDULE_DAY_BITS
    assert transitions[0] == (0, 1600)
    assert trv_zbt._sonoff_trvzbt_format_minutes(90) == "01:30"
    assert trv_zbt._sonoff_trvzbt_uint8(255, "value") == 255
    with pytest.raises(ValueError, match="uint8"):
        trv_zbt._sonoff_trvzbt_uint8(-1, "value")

    schedule = trv_zbt._sonoff_trvzbt_default_schedule(0, day)
    trv_zbt._sonoff_trvzbt_cache_schedule(cluster, schedule)
    trv_zbt._sonoff_trvzbt_update_editor_from_schedule(cluster, schedule)
    trv_zbt._sonoff_trvzbt_load_cached_schedule(cluster)
    assert (
        trv_zbt._sonoff_trvzbt_get_attr(
            cluster, trv_zbt.SONOFF_TRVZBT_SCHEDULE_EDITOR_GROUP_ATTR
        )
        == 0
    )
    assert trv_zbt._sonoff_trvzbt_schedule_cache(cluster)[(0, day)]["schedule"]

    first_time = trv_zbt.SONOFF_TRVZBT_SCHEDULE_EDITOR_PERIOD_TIME_ATTRS[1]
    cluster._update_attribute(first_time, 30)
    with pytest.raises(ValueError, match="00:00"):
        trv_zbt._sonoff_trvzbt_validate_schedule_times(cluster)

    entity = type(
        "Entity",
        (),
        {"unique_id_suffix": "local_temperature_calibration", "cluster_id": 0},
    )()
    assert trv_zbt._sonoff_trvzbt_is_replaced_default_entity(entity)


def _trv_zbt_device(zigpy_device_from_v2_quirk):
    """Create a quirked device without starting delayed background reads."""

    completed_task = mock.Mock()
    completed_task.done.return_value = True
    with mock.patch.object(
        trv_zbt.asyncio,
        "create_task",
        side_effect=lambda coroutine: (coroutine.close(), completed_task)[1],
    ):
        device = zigpy_device_from_v2_quirk(
            "SONOFF",
            "TRV-ZBT",
            cluster_ids={
                1: {
                    Thermostat.cluster_id: ClusterType.Server,
                    CustomSonoffCluster.cluster_id: ClusterType.Server,
                }
            },
        )
    return (
        device.endpoints[1].in_clusters[CustomSonoffCluster.cluster_id],
        device.endpoints[1].in_clusters[Thermostat.cluster_id],
    )


async def test_trv_zbt_command_paths_update_device_state(zigpy_device_from_v2_quirk):
    """Editor commands serialize expected payloads and update virtual state."""

    cluster, thermostat = _trv_zbt_device(zigpy_device_from_v2_quirk)
    thermostat._update_attribute(
        thermostat.AttributeDefs.occupied_heating_setpoint.id, 1900
    )
    thermostat._update_attribute(thermostat.AttributeDefs.system_mode.id, 1)

    schedule_group_raw = mock.AsyncMock()
    bluetooth_pairing = mock.AsyncMock()
    parent_write = mock.AsyncMock(return_value=({}, {}))
    sleep = mock.AsyncMock()
    with (
        mock.patch.object(cluster, "schedule_group_raw", schedule_group_raw),
        mock.patch.object(cluster, "bluetooth_pairing", bluetooth_pairing),
        mock.patch.object(trv_zbt.CustomCluster, "write_attributes", parent_write),
        mock.patch.object(trv_zbt.asyncio, "sleep", sleep),
    ):
        await cluster.schedule_apply()
        await cluster.schedule_fetch()
        assert schedule_group_raw.await_count == 2
        assert schedule_group_raw.await_args_list[1].kwargs["data"] == b"\x01\x00\x00"

        cluster._update_attribute(
            trv_zbt.SONOFF_TRVZBT_TEMPORARY_MODE_EDITOR_MODE_ATTR,
            trv_zbt.SonoffTemporaryModeEditor.Boost,
        )
        cluster._update_attribute(
            trv_zbt.SONOFF_TRVZBT_TEMPORARY_MODE_EDITOR_DURATION_ATTR, 60
        )
        await cluster.temporary_mode_apply()
        assert cluster._attr_cache[cluster.AttributeDefs.temporary_mode.id] == 0
        assert parent_write.await_count == 2

        cluster._update_attribute(
            trv_zbt.SONOFF_TRVZBT_TEMPORARY_MODE_EDITOR_MODE_ATTR,
            trv_zbt.SonoffTemporaryModeEditor.Timer,
        )
        cluster._update_attribute(
            trv_zbt.SONOFF_TRVZBT_TEMPORARY_MODE_EDITOR_DURATION_ATTR, 120
        )
        cluster._update_attribute(
            trv_zbt.SONOFF_TRVZBT_TEMPORARY_MODE_EDITOR_TARGET_TEMPERATURE_ATTR,
            2000,
        )
        await cluster.temporary_mode_apply()
        assert (
            cluster._attr_cache[cluster.AttributeDefs.timer_mode_target_temperature.id]
            == 2000
        )

        await cluster.bluetooth_pairing_press()
        bluetooth_pairing.assert_awaited_once()


async def test_trv_zbt_local_reads_writes_and_private_responses(
    zigpy_device_from_v2_quirk,
):
    """Virtual attributes remain local and private responses update their cache."""

    cluster, thermostat = _trv_zbt_device(zigpy_device_from_v2_quirk)
    calibration_name = thermostat.AttributeDefs.local_temperature_calibration.name
    thermostat.read_attributes = mock.AsyncMock(
        return_value=({calibration_name: 4}, {})
    )
    thermostat.write_attributes = mock.AsyncMock(return_value=({}, {}))

    success, failure = await cluster.read_attributes(
        [
            cluster.AttributeDefs.schedule_editor_group.name,
            cluster.AttributeDefs.schedule_editor_day.name,
            cluster.AttributeDefs.local_temperature_offset.name,
        ]
    )
    assert not failure
    assert success[cluster.AttributeDefs.local_temperature_offset.name] == 4

    await cluster.write_attributes(
        {
            cluster.AttributeDefs.local_temperature_offset.name: 2,
            cluster.AttributeDefs.schedule_editor_group.name: 1,
            cluster.AttributeDefs.schedule_editor_day.name: 2,
        }
    )
    thermostat.write_attributes.assert_awaited_once()
    assert cluster._attr_cache[trv_zbt.SONOFF_TRVZBT_SCHEDULE_EDITOR_GROUP_ATTR] == 1

    await cluster.write_attributes(
        {cluster.AttributeDefs.temporary_mode.name: trv_zbt.SonoffTemporaryMode.None_}
    )
    assert cluster._attr_cache[cluster.AttributeDefs.temporary_mode.id] == 255

    header = foundation.ZCLHeader()
    with (
        mock.patch.object(cluster, "_sonoff_trvzbt_schedule_temporary_mode_read"),
        mock.patch.object(cluster, "_sonoff_trvzbt_schedule_device_work_mode_read"),
    ):
        header.command_id = 0x13
        cluster.handle_cluster_request(header, [b"\x01\x01\x00\x01"])
        assert cluster._attr_cache[trv_zbt.SONOFF_TRVZBT_SCHEDULE_STATUS_ATTR] == "fail"
        header.command_id = 0x10
        cluster.handle_cluster_request(header, [b"\x02\x01"])
        assert (
            cluster._attr_cache[trv_zbt.SONOFF_TRVZBT_BLUETOOTH_PAIRING_STATUS_ATTR]
            == "fail"
        )


async def test_trv_zbt_delayed_reads_and_temporary_exit(zigpy_device_from_v2_quirk):
    """Delayed reads retry failures and exiting temporary mode restores thermostat state."""

    cluster, thermostat = _trv_zbt_device(zigpy_device_from_v2_quirk)
    sleep = mock.AsyncMock()
    temporary_name = cluster.AttributeDefs.temporary_mode.name
    work_mode_name = cluster.AttributeDefs.device_work_mode.name
    with mock.patch.object(trv_zbt.asyncio, "sleep", sleep):
        cluster.read_attributes = mock.AsyncMock(
            side_effect=[RuntimeError("offline"), ({temporary_name: 1}, {})]
        )
        await cluster._sonoff_trvzbt_read_temporary_mode_later(delay=0)
        cluster.read_attributes = mock.AsyncMock(
            side_effect=[RuntimeError("offline"), ({work_mode_name: 3}, {})]
        )
        await cluster._sonoff_trvzbt_read_device_work_mode_later(delay=0)

        thermostat.sonoff_trvzbt_send_setpoint_signal = mock.AsyncMock(
            return_value=1950
        )
        thermostat.write_attributes = mock.AsyncMock(return_value=({}, {}))
        cluster._sonoff_trvzbt_pre_temporary_state = {
            "occupied_heating_setpoint": 1950,
            "system_mode": 1,
        }
        with (
            mock.patch.object(cluster, "_sonoff_trvzbt_schedule_temporary_mode_read"),
            mock.patch.object(cluster, "_sonoff_trvzbt_schedule_device_work_mode_read"),
        ):
            await cluster.temporary_mode_exit()

    thermostat.sonoff_trvzbt_send_setpoint_signal.assert_awaited_once_with(
        setpoint=1950
    )
    assert cluster._attr_cache[cluster.AttributeDefs.temporary_mode.id] == 255
    assert cluster._sonoff_trvzbt_pre_temporary_state is None


async def test_trv_zbt_mixed_virtual_and_real_attribute_io(
    zigpy_device_from_v2_quirk,
):
    """ID-based editor writes stay local while normal attributes are forwarded."""

    cluster, thermostat = _trv_zbt_device(zigpy_device_from_v2_quirk)
    parent_read = mock.AsyncMock(return_value=({"open_window": 1}, {}))
    parent_write = mock.AsyncMock(return_value=({"open_window": 1}, {}))
    with (
        mock.patch.object(trv_zbt.CustomCluster, "read_attributes", parent_read),
        mock.patch.object(trv_zbt.CustomCluster, "write_attributes", parent_write),
    ):
        success, failure = await cluster.read_attributes(
            [cluster.AttributeDefs.open_window.name]
        )
        assert success == {"open_window": 1}
        assert not failure

        period_time = trv_zbt.SONOFF_TRVZBT_SCHEDULE_EDITOR_PERIOD_TIME_ATTRS[2]
        period_temperature = trv_zbt.SONOFF_TRVZBT_SCHEDULE_EDITOR_PERIOD_TEMP_ATTRS[2]
        await cluster.write_attributes(
            {
                period_time: 180,
                period_temperature: 1900,
                trv_zbt.SONOFF_TRVZBT_TEMPORARY_MODE_EDITOR_DURATION_ATTR: 180,
                cluster.AttributeDefs.open_window.name: 1,
            }
        )
        assert cluster._attr_cache[period_time] == 180
        assert cluster._attr_cache[period_temperature] == 1900
        assert (
            cluster._attr_cache[
                trv_zbt.SONOFF_TRVZBT_TEMPORARY_MODE_EDITOR_DURATION_ATTR
            ]
            == 180
        )
        parent_write.assert_awaited_once()

        with pytest.raises(ValueError, match="at least"):
            await cluster.write_attributes({period_time: 0})
        assert cluster._attr_cache[period_time] == 180


async def test_trv_zbt_temporary_mode_validation_and_capture(
    zigpy_device_from_v2_quirk,
):
    """Temporary mode validates limits and captures missing thermostat state."""

    cluster, thermostat = _trv_zbt_device(zigpy_device_from_v2_quirk)
    setpoint_name = thermostat.AttributeDefs.occupied_heating_setpoint.name
    system_mode_name = thermostat.AttributeDefs.system_mode.name
    thermostat.read_attributes = mock.AsyncMock(
        return_value=({setpoint_name: 2100, system_mode_name: 4}, {})
    )
    with mock.patch.object(trv_zbt.asyncio, "sleep", mock.AsyncMock()):
        await cluster._sonoff_trvzbt_capture_pre_temporary_state()
        assert cluster._sonoff_trvzbt_pre_temporary_state == {
            "occupied_heating_setpoint": 2100,
            "system_mode": 4,
        }

        cluster._sonoff_trvzbt_pre_temporary_state = None
        cluster._update_attribute(
            trv_zbt.SONOFF_TRVZBT_TEMPORARY_MODE_EDITOR_MODE_ATTR,
            trv_zbt.SonoffTemporaryModeEditor.Timer,
        )
        cluster._update_attribute(
            trv_zbt.SONOFF_TRVZBT_TEMPORARY_MODE_EDITOR_DURATION_ATTR, 61
        )
        with pytest.raises(ValueError, match="whole number"):
            await cluster.temporary_mode_apply()

        cluster._update_attribute(
            trv_zbt.SONOFF_TRVZBT_TEMPORARY_MODE_EDITOR_DURATION_ATTR, 60
        )
        cluster._update_attribute(
            trv_zbt.SONOFF_TRVZBT_TEMPORARY_MODE_EDITOR_TARGET_TEMPERATURE_ATTR,
            400,
        )
        with pytest.raises(ValueError, match="5-30"):
            await cluster.temporary_mode_apply()


async def test_trv_zbt_thermostat_setpoint_and_boost_protection(
    zigpy_device_from_v2_quirk,
):
    """Thermostat writes are blocked during Boost and restore a cached setpoint."""

    private_cluster, thermostat = _trv_zbt_device(zigpy_device_from_v2_quirk)
    setpoint_attr = thermostat.AttributeDefs.occupied_heating_setpoint
    parent_write = mock.AsyncMock(return_value=({}, {}))
    with mock.patch.object(trv_zbt.CustomCluster, "write_attributes", parent_write):
        assert not thermostat._is_boost_mode_active()
        private_cluster._update_attribute(
            private_cluster.AttributeDefs.temporary_mode.id,
            trv_zbt.SonoffTemporaryMode.Boost,
        )
        assert thermostat._is_boost_mode_active()
        with pytest.raises(ValueError, match="Boost"):
            await thermostat.write_attributes({setpoint_attr.name: 2000})

        private_cluster._update_attribute(
            private_cluster.AttributeDefs.temporary_mode.id,
            trv_zbt.SonoffTemporaryMode.Timer,
        )
        thermostat.read_attributes = mock.AsyncMock(
            return_value=({setpoint_attr.id: 2050}, {})
        )
        thermostat._attr_cache[setpoint_attr.id] = None
        assert await thermostat.sonoff_trvzbt_send_setpoint_signal() == 2050
        assert thermostat._attr_cache[setpoint_attr.id] == 2050
        await thermostat.write_attributes({setpoint_attr.name: 2100})


async def test_trv_zbt_temporary_mode_and_attribute_error_paths(
    zigpy_device_from_v2_quirk,
):
    """Invalid editor values reject unsafe writes without forwarding malformed data."""

    cluster, _thermostat = _trv_zbt_device(zigpy_device_from_v2_quirk)
    with mock.patch.object(trv_zbt.asyncio, "sleep", mock.AsyncMock()):
        cluster._update_attribute(
            trv_zbt.SONOFF_TRVZBT_TEMPORARY_MODE_EDITOR_MODE_ATTR, 99
        )
        with pytest.raises(ValueError, match="None, Boost or Timer"):
            await cluster.temporary_mode_apply()

        cluster._update_attribute(
            trv_zbt.SONOFF_TRVZBT_TEMPORARY_MODE_EDITOR_MODE_ATTR,
            trv_zbt.SonoffTemporaryModeEditor.Boost,
        )
        cluster._update_attribute(
            trv_zbt.SONOFF_TRVZBT_TEMPORARY_MODE_EDITOR_DURATION_ATTR, -60
        )
        with pytest.raises(ValueError, match="must not be negative"):
            await cluster.temporary_mode_apply()

        cluster._update_attribute(
            trv_zbt.SONOFF_TRVZBT_TEMPORARY_MODE_EDITOR_DURATION_ATTR, 181 * 60
        )
        parent_write = mock.AsyncMock(return_value=({}, {}))
        with mock.patch.object(trv_zbt.CustomCluster, "write_attributes", parent_write):
            await cluster.temporary_mode_apply()
        assert (
            cluster._attr_cache[
                trv_zbt.SONOFF_TRVZBT_TEMPORARY_MODE_EDITOR_DURATION_ATTR
            ]
            == 180 * 60
        )

    parent_read = mock.AsyncMock(return_value=({}, {"unknown": 1}))
    with mock.patch.object(trv_zbt.CustomCluster, "read_attributes", parent_read):
        _success, failure = await cluster.read_attributes(["unknown"])
    assert failure == {"unknown": 1}


async def test_trv_zbt_write_duration_limits(zigpy_device_from_v2_quirk):
    """Direct temporary-mode writes enforce the limits reported by the device."""

    cluster, _thermostat = _trv_zbt_device(zigpy_device_from_v2_quirk)
    with pytest.raises(ValueError, match="0-180"):
        await cluster.write_attributes(
            {
                cluster.AttributeDefs.temporary_mode.name: trv_zbt.SonoffTemporaryMode.Boost,
                cluster.AttributeDefs.temporary_mode_duration.name: 181 * 60,
            }
        )

    with pytest.raises(ValueError, match="0-1440"):
        await cluster.write_attributes(
            {
                cluster.AttributeDefs.temporary_mode.name: trv_zbt.SonoffTemporaryMode.Timer,
                cluster.AttributeDefs.temporary_mode_duration.name: 1441 * 60,
            }
        )


def test_trv_zbt_protocol_error_guards():
    """Malformed protocol values are ignored or rejected predictably."""

    assert trv_zbt.SonoffHvacMessageNotification(b"\x01").serialize() == b"\x01"
    assert trv_zbt.convert_sonoff_trvzbt_fault_code(0x0A020081) == (
        "Temperature sensor issue, Unknown"
    )
    assert trv_zbt.convert_sonoff_trvzbt_open_window_detected(object()) is None
    assert (
        trv_zbt.parse_sonoff_trvzbt_schedule_group(
            b"\x01\x00\x00\x02\x02\x01\xa1\x05\x40\x06\x00\x00\x40\x06"
        )["schedule"]
        == "00:00/16"
    )
    with pytest.raises(ValueError, match="uint16"):
        trv_zbt._sonoff_trvzbt_uint16(-1, "value")
    with pytest.raises(ValueError, match="int16"):
        trv_zbt._sonoff_trvzbt_int16(32768, "value")
