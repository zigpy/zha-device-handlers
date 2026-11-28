"""Tests for the Tuya X5H wall thermostat."""

import datetime
from unittest import mock

import pytest
import time_machine
from zha.application import Platform
from zha.quirks import DEVICE_REGISTRY
from zigpy.zcl import foundation
from zigpy.zcl.clusters.hvac import Thermostat

from tests.common import ClusterListener, wait_for_zigpy_tasks
from tests.zha_helpers import join_device_from_diagnostics, zha_gateway
import zhaquirks
from zhaquirks.tuya import TUYA_SET_TIME, TuyaCommand
from zhaquirks.tuya.tuya_x5h_thermostat import (
    X5HManufCluster,
    X5HThermostat,
    schedule_from_raw,
    schedule_to_raw,
    setpoint_to_dp,
    signed16,
)

zhaquirks.setup()

MANUFACTURER = "_TZE200_2ekuz3dz"
SCHEDULE_TEXT = (
    "06:00/20.5 08:00/15 11:30/15 13:30/15 17:00/22 22:00/15 06:00/20 22:00/15"
)
SCHEDULE_RAW = bytes.fromhex(
    "060000cd080000960b1e00960d1e0096110000dc16000096060000c816000096"
)
DIAGNOSTICS = "tze200-2ekuz3dz-ts0601-0x00000044.json"
IEEE = "ab:cd:ef:12:92:5b:00:57"


@pytest.fixture
def x5h(zigpy_device_from_v2_quirk):
    """X5H thermostat with the quirk applied."""
    return zigpy_device_from_v2_quirk(MANUFACTURER, "TS0601")


def sent_datapoints(cluster, request_mock: mock.MagicMock) -> list:
    """Decode the Tuya datapoints of all requests sent through the endpoint."""
    datapoints = []
    for call in request_mock.call_args_list:
        if call.kwargs.get("cluster", cluster.cluster_id) != cluster.cluster_id:
            continue
        _, cmd = cluster.deserialize(call.kwargs["data"])
        if isinstance(cmd.data, TuyaCommand):
            datapoints.extend(cmd.data.datapoints)
    return datapoints


@pytest.mark.parametrize(
    ("centidegrees", "expected"),
    [(2140, 215), (2150, 215), (2125, 215), (2120, 210), (2175, 220), (500, 50)],
)
def test_setpoint_rounding(centidegrees, expected):
    """Setpoints are rounded to the 0.5 C grid of the thermostat, halves up."""
    assert setpoint_to_dp(centidegrees) == expected


def test_signed_local_temperature():
    """Local temperature is a signed 16 bit value."""
    assert signed16(213) == 213
    assert signed16(0xFFF6) == -10


def test_schedule_conversion():
    """The raw schedule converts to the text format and back."""
    assert schedule_from_raw(SCHEDULE_RAW) == SCHEDULE_TEXT
    assert bytes(schedule_to_raw(SCHEDULE_TEXT)) == SCHEDULE_RAW
    assert bytes(schedule_to_raw("  " + SCHEDULE_TEXT.replace(" ", "   "))) == (
        SCHEDULE_RAW
    )


@pytest.mark.parametrize(
    "text",
    [
        "06:00/20 08:00/15",  # too few periods
        SCHEDULE_TEXT.replace("06:00/20.5", "24:00/20.5"),  # invalid hour
        SCHEDULE_TEXT.replace("06:00/20.5", "06:60/20.5"),  # invalid minute
        SCHEDULE_TEXT.replace("06:00/20.5", "06:00/20.3"),  # not a 0.5 step
        SCHEDULE_TEXT.replace("06:00/20.5", "06:00/61"),  # out of range
    ],
)
def test_schedule_invalid(text):
    """Invalid schedules are rejected."""
    with pytest.raises(ValueError):
        schedule_to_raw(text)


@pytest.mark.parametrize(
    ("msg", "attr", "value"),
    [
        (
            b"\t\x13\x02\x00\x06\x01\x01\x00\x01\x01",
            Thermostat.AttributeDefs.system_mode,
            Thermostat.SystemMode.Heat,
        ),  # dp 1, on
        (
            b"\t\x15\x02\x00\x08\x10\x02\x00\x04\x00\x00\x00\xd7",
            Thermostat.AttributeDefs.occupied_heating_setpoint,
            2150,
        ),  # dp 16, 21.5 C
        (
            b"\t\x16\x02\x00\t\x18\x02\x00\x04\x00\x00\x00\xd5",
            Thermostat.AttributeDefs.local_temperature,
            2130,
        ),  # dp 24, 21.3 C
        (
            b"\t\x1c\x02\x00\x0f\x03\x01\x00\x01\x01",
            Thermostat.AttributeDefs.running_state,
            Thermostat.RunningState.Heat_State_On,
        ),  # dp 3, heating
    ],
)
async def test_handle_get_data(x5h, msg, attr, value):
    """Datapoint reports update the thermostat cluster."""
    mcu = x5h.endpoints[1].tuya_manufacturer
    listener = ClusterListener(x5h.endpoints[1].thermostat)

    hdr, data = mcu.deserialize(msg)
    with mock.patch.object(mcu, "send_time"):
        mcu.handle_cluster_request(hdr, data)

    assert listener.attribute_updates == [(attr.id, value)]


async def test_schedule_report(x5h):
    """A DP 30 report updates the schedule attribute."""
    mcu = x5h.endpoints[1].tuya_manufacturer
    msg = b"\t\x20\x02\x00\x30\x1e\x00\x00\x20" + SCHEDULE_RAW

    hdr, data = mcu.deserialize(msg)
    with mock.patch.object(mcu, "send_time"):
        mcu.handle_cluster_request(hdr, data)

    assert mcu.get("schedule") == SCHEDULE_TEXT


async def test_setpoint_write_rounds(x5h):
    """A 21.4 C setpoint is sent as 21.5 C."""
    ep = x5h.endpoints[1]
    with mock.patch.object(
        ep, "request", return_value=foundation.Status.SUCCESS
    ) as request:
        await ep.thermostat.write_attributes({"occupied_heating_setpoint": 2140})
        await wait_for_zigpy_tasks()

    (datapoint,) = sent_datapoints(ep.tuya_manufacturer, request)
    assert datapoint.dp == 16
    assert datapoint.data.payload == 215


async def test_schedule_write(x5h):
    """The schedule text is sent as the raw DP 30."""
    ep = x5h.endpoints[1]
    mcu = ep.tuya_manufacturer
    with mock.patch.object(
        ep, "request", return_value=foundation.Status.SUCCESS
    ) as request:
        await mcu.write_attributes({"schedule": SCHEDULE_TEXT})
        await wait_for_zigpy_tasks()

    (datapoint,) = sent_datapoints(ep.tuya_manufacturer, request)
    assert datapoint.dp == 30
    assert bytes(datapoint.data.payload) == SCHEDULE_RAW
    assert mcu.get("schedule") == SCHEDULE_TEXT


async def test_schedule_write_invalid(x5h):
    """An invalid schedule is not sent."""
    ep = x5h.endpoints[1]
    with mock.patch.object(ep, "request") as request, pytest.raises(ValueError):
        await ep.tuya_manufacturer.write_attributes({"schedule": "06:00/20"})

    request.assert_not_called()


async def test_factory_reset_write(x5h):
    """The factory reset button writes DP 39."""
    ep = x5h.endpoints[1]
    with mock.patch.object(
        ep, "request", return_value=foundation.Status.SUCCESS
    ) as request:
        await ep.tuya_manufacturer.write_attributes({"factory_reset": 1})
        await wait_for_zigpy_tasks()

    (datapoint,) = sent_datapoints(ep.tuya_manufacturer, request)
    assert datapoint.dp == 39
    assert datapoint.data.payload == 1


def _sent_time_stamps(request_mock: mock.MagicMock) -> list[int]:
    stamps = []
    for call in request_mock.call_args_list:
        if call.kwargs["command_id"] == TUYA_SET_TIME:
            raw = call.kwargs["data"][-8:]
            stamps.append(int.from_bytes(raw[:4], "big"))
            assert raw[:4] == raw[4:]
    return stamps


@time_machine.travel(datetime.datetime(2026, 1, 15, 10, 30, 0), tick=False)
async def test_time_sync_compensated(x5h):
    """The time reply carries local time minus the 8 hours the firmware adds."""
    ep = x5h.endpoints[1]
    with mock.patch.object(
        ep, "request", return_value=foundation.Status.SUCCESS
    ) as request:
        ep.tuya_manufacturer.handle_set_time_request(0)
        await wait_for_zigpy_tasks()

    (stamp,) = _sent_time_stamps(request)
    local = datetime.datetime.now() - datetime.datetime(1970, 1, 1)
    assert stamp == int(local.total_seconds()) - 8 * 3600


@time_machine.travel(datetime.datetime(2026, 1, 15, 3, 0, 0), tick=False)
async def test_time_sync_skipped_at_night(x5h):
    """No time is sent before 08:00, the display would show 24:00 to 31:59."""
    ep = x5h.endpoints[1]
    with mock.patch.object(
        ep, "request", return_value=foundation.Status.SUCCESS
    ) as request:
        ep.tuya_manufacturer.handle_set_time_request(0)
        await wait_for_zigpy_tasks()

    assert _sent_time_stamps(request) == []


@time_machine.travel(datetime.datetime(2026, 1, 15, 12, 0, 0), tick=False)
async def test_time_pushed_on_traffic_once(x5h):
    """Device traffic pushes the time, at most once an hour."""
    ep = x5h.endpoints[1]
    mcu = ep.tuya_manufacturer
    msg = b"\t\x13\x02\x00\x06\x01\x01\x00\x01\x01"
    with mock.patch.object(
        ep, "request", return_value=foundation.Status.SUCCESS
    ) as request:
        for _ in range(3):
            hdr, data = mcu.deserialize(msg)
            mcu.handle_cluster_request(hdr, data)
        await wait_for_zigpy_tasks()

    assert len(_sent_time_stamps(request)) == 1


async def test_entities():
    """The quirk creates its entities and drops the unsupported thermostat sensors."""
    async with zha_gateway() as gateway:
        device = await join_device_from_diagnostics(
            gateway, DIAGNOSTICS, DEVICE_REGISTRY
        )
        assert isinstance(device.device.endpoints[1].thermostat, X5HThermostat)
        assert isinstance(device.device.endpoints[1].tuya_manufacturer, X5HManufCluster)

        unique_ids = {
            (platform, entity.unique_id)
            for (platform, _), entity in device.platform_entities.items()
        }
        for platform, suffix in [
            (Platform.CLIMATE, ""),
            (Platform.SENSOR, "-1-schedule"),
            (Platform.BUTTON, "-1-factory_reset"),
            (Platform.SELECT, "-1-week"),
            (Platform.SELECT, "-1-preset_mode"),
            (Platform.SELECT, "-1-sensor_selection"),
            (Platform.SELECT, "-1-backlight_brightness"),
            (Platform.NUMBER, "-1-local_temperature_calibration"),
            (Platform.NUMBER, "-1-deadzone_temperature"),
            (Platform.NUMBER, "-1-heating_temp_limit"),
            (Platform.NUMBER, "-1-upper_temp"),
            (Platform.SWITCH, "-1-child_lock"),
            (Platform.SWITCH, "-1-frost_protection"),
            (Platform.SWITCH, "-1-sound"),
            (Platform.SENSOR, "-1-1026"),
        ]:
            if platform is Platform.CLIMATE:
                assert any(
                    p is Platform.CLIMATE and uid == f"{IEEE}-1"
                    for p, uid in unique_ids
                )
            else:
                assert (platform, f"{IEEE}{suffix}") in unique_ids, suffix

        for suffix in (
            "pi_heating_demand",
            "setpoint_change_source",
            "setpoint_change_source_timestamp",
        ):
            assert (Platform.SENSOR, f"{IEEE}-1-513-{suffix}") not in unique_ids
