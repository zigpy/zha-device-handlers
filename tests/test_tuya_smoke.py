"""Tests for Tuya Smoke Detector."""

import asyncio
from unittest import mock

import pytest
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.security import IasZone

from tests.common import ClusterListener, wait_for_zigpy_tasks
import zhaquirks
from zhaquirks.tuya import TuyaCommand, TuyaData, TuyaDatapointData, tuya_smoke
from zhaquirks.tuya.mcu import TuyaMCUCluster

zhaquirks.setup()


@pytest.mark.parametrize(
    "model,manuf,battery_test",
    [
        ("_TZE200_dq1mfjug", "TS0601", []),
        ("_TZE200_m9skfctm", "TS0601", []),
        ("_TZE200_rccxox8p", "TS0601", []),
        ("_TZE284_rccxox8p", "TS0601", []),
        ("_TZE200_vzekyi4c", "TS0601", []),
        ("_TZE204_vawy74yh", "TS0601", []),
        (
            "_TZE200_ntcy3xu1",
            "TS0601",
            (
                (b"\x09\x3a\x02\x00\x12\x0e\x04\x00\x01\x02", 200),
                (b"\x09\x3a\x02\x00\x12\x0e\x04\x00\x01\x01", 80),
                (b"\x09\x3a\x02\x00\x12\x0e\x04\x00\x01\x00", 10),
            ),
        ),
        (
            "_TZE204_ntcy3xu1",
            "TS0601",
            (
                (b"\x09\x3a\x02\x00\x12\x0e\x04\x00\x01\x02", 200),
                (b"\x09\x3a\x02\x00\x12\x0e\x04\x00\x01\x01", 80),
                (b"\x09\x3a\x02\x00\x12\x0e\x04\x00\x01\x00", 10),
            ),
        ),
        ("_TZE284_0zaf1cr8", "TS0601", []),
        ("_TZE204_kgaxpvxr", "TS0601", []),
    ],
)
async def test_handle_get_data(zigpy_device_from_v2_quirk, model, manuf, battery_test):
    """Test handle_get_data for multiple attributes."""

    zone_status_id = IasZone.AttributeDefs.zone_status.id

    quirked = zigpy_device_from_v2_quirk(model, manuf)
    ep = quirked.endpoints[1]

    assert ep.tuya_manufacturer is not None
    assert isinstance(ep.tuya_manufacturer, TuyaMCUCluster)

    ias_listener = ClusterListener(ep.ias_zone)

    message = b"\x09\x39\x02\x00\x11\x01\x04\x00\x01\x00"
    hdr, data = ep.tuya_manufacturer.deserialize(message)

    status = ep.tuya_manufacturer.handle_get_data(data.data)
    assert status == foundation.Status.SUCCESS

    assert len(ias_listener.attribute_updates) == 1
    assert ias_listener.attribute_updates[0][0] == zone_status_id
    assert ias_listener.attribute_updates[0][1] == IasZone.ZoneStatus.Alarm_1

    assert ep.ias_zone.get(zone_status_id) == IasZone.ZoneStatus.Alarm_1

    message = b"\x09\x3b\x02\x00\x13\x01\x04\x00\x01\x01"
    hdr, data = ep.tuya_manufacturer.deserialize(message)

    status = ep.tuya_manufacturer.handle_get_data(data.data)
    assert status == foundation.Status.SUCCESS

    assert len(ias_listener.attribute_updates) == 2
    assert ias_listener.attribute_updates[1][0] == zone_status_id
    assert ias_listener.attribute_updates[1][1] == 0

    assert ep.ias_zone.get(zone_status_id) == 0

    for message, state in battery_test:
        power_listener = ClusterListener(ep.power)

        hdr, data = ep.tuya_manufacturer.deserialize(message)
        status = ep.tuya_manufacturer.handle_get_data(data.data)
        assert status == foundation.Status.SUCCESS

        assert len(power_listener.attribute_updates) == 1
        assert power_listener.attribute_updates[0][1] == state


async def test_tuya_smoke_sensor_attribute_update(zigpy_device_from_v2_quirk):
    """Test update_attribute on Tuya smoke sensor."""

    device = zigpy_device_from_v2_quirk("_TZ3210_up3pngle", "TS0205")

    tuya_cluster = device.endpoints[1].tuya_manufacturer
    tuya_listener = ClusterListener(tuya_cluster)

    ias_cluster = device.endpoints[1].ias_zone
    ias_listener = ClusterListener(ias_cluster)

    zone_status_id = IasZone.AttributeDefs.zone_status.id

    # check that updating smoke attribute also updates zone status on the Ias Zone cluster

    # turn on smoke alarm
    tuya_cluster.update_attribute(0x0401, 1)
    assert len(tuya_listener.attribute_updates) == 1
    assert len(ias_listener.attribute_updates) == 1
    assert ias_listener.attribute_updates[0][0] == zone_status_id
    assert ias_listener.attribute_updates[0][1] == 0
    # turn off smoke alarm
    tuya_cluster.update_attribute(0x0401, 0)
    assert len(tuya_listener.attribute_updates) == 2
    assert len(ias_listener.attribute_updates) == 2
    assert ias_listener.attribute_updates[1][0] == zone_status_id
    assert ias_listener.attribute_updates[1][1] == IasZone.ZoneStatus.Alarm_1


def _pa44z_report(cluster, dp, value):
    """Feed one datapoint report to the PA-44Z Tuya cluster."""
    command = TuyaCommand(
        status=0, tsn=1, datapoints=[TuyaDatapointData(dp, TuyaData(value))]
    )
    assert cluster.handle_get_data(command) == foundation.Status.SUCCESS


@pytest.fixture
async def pa44z(zigpy_device_from_v2_quirk, monkeypatch):
    """PA-44Z device with short timers."""
    monkeypatch.setattr(tuya_smoke, "ALARM_CLEAR_S", 0.2)
    device = zigpy_device_from_v2_quirk("_TZE284_rccxox8p", "TS0601")
    return device.endpoints[1]


def _alarm(ep):
    return ep.ias_zone.get(IasZone.AttributeDefs.zone_status.name)


async def test_pa44z_alarm_clears_after_heartbeat_stops(pa44z):
    """Smoke stays on while DP 101 = false reports arrive, then clears."""
    tuya = pa44z.tuya_manufacturer
    alarm = IasZone.ZoneStatus.Alarm_1

    _pa44z_report(tuya, 1, t.enum8(0))
    assert _alarm(pa44z) == alarm

    for _ in range(3):
        await asyncio.sleep(0.15)
        _pa44z_report(tuya, 101, False)
        assert _alarm(pa44z) == alarm

    await asyncio.sleep(0.3)
    assert _alarm(pa44z) == 0


async def test_pa44z_self_test_done_clears_alarm(pa44z):
    """DP 101 = true clears the alarm now; the value follows the device."""
    tuya = pa44z.tuya_manufacturer

    _pa44z_report(tuya, 1, t.enum8(0))
    assert _alarm(pa44z) == IasZone.ZoneStatus.Alarm_1

    _pa44z_report(tuya, 101, True)
    assert _alarm(pa44z) == 0
    assert tuya.get("self_test_done")

    # No reset of its own: stays on until the device reports false.
    await asyncio.sleep(0.3)
    assert tuya.get("self_test_done")
    _pa44z_report(tuya, 101, False)
    assert not tuya.get("self_test_done")


async def test_pa44z_heartbeat_without_alarm_does_nothing(pa44z):
    """DP 101 = false without an active alarm does not raise one."""
    _pa44z_report(pa44z.tuya_manufacturer, 101, False)
    await asyncio.sleep(0.3)
    assert not _alarm(pa44z)


async def test_pa44z_smoke_report_alone_never_clears(pa44z):
    """Without heartbeats (DP 101 = false) the timer never clears the alarm."""
    tuya = pa44z.tuya_manufacturer
    _pa44z_report(tuya, 1, t.enum8(0))
    await asyncio.sleep(0.5)
    assert _alarm(pa44z) == IasZone.ZoneStatus.Alarm_1
    assert not tuya.get(tuya_smoke.ATTR_TIMER_RUNNING)


async def test_pa44z_end_report_clears_and_stops_timer(pa44z):
    """A DP 1 end report clears the alarm and stops the clear timer."""
    tuya = pa44z.tuya_manufacturer
    _pa44z_report(tuya, 1, t.enum8(0))
    _pa44z_report(tuya, 101, False)
    assert tuya.get(tuya_smoke.ATTR_TIMER_RUNNING)

    _pa44z_report(tuya, 1, t.enum8(1))
    assert _alarm(pa44z) == 0
    assert not tuya.get(tuya_smoke.ATTR_TIMER_RUNNING)
    assert tuya._alarm_handle is None


async def test_pa44z_timer_flag_follows_alarm(pa44z):
    """The saved flag is set by the first heartbeat and cleared with the alarm."""
    tuya = pa44z.tuya_manufacturer
    _pa44z_report(tuya, 1, t.enum8(0))
    assert not tuya.get(tuya_smoke.ATTR_TIMER_RUNNING)
    _pa44z_report(tuya, 101, False)
    assert tuya.get(tuya_smoke.ATTR_TIMER_RUNNING)
    await asyncio.sleep(0.3)
    assert _alarm(pa44z) == 0
    assert not tuya.get(tuya_smoke.ATTR_TIMER_RUNNING)


@pytest.mark.parametrize("timer_was_running", [True, False])
async def test_pa44z_restored_alarm(pa44z, timer_was_running):
    """A restored alarm clears after startup only if its timer was running."""
    # Values restored from the database after the quirk is created.
    pa44z.tuya_manufacturer.update_attribute(
        tuya_smoke.ATTR_TIMER_RUNNING, timer_was_running
    )
    pa44z.ias_zone.update_attribute(
        IasZone.AttributeDefs.zone_status.name, IasZone.ZoneStatus.Alarm_1
    )
    await asyncio.sleep(0.3)
    expected = 0 if timer_was_running else IasZone.ZoneStatus.Alarm_1
    assert _alarm(pa44z) == expected


@pytest.mark.parametrize("value", [True, False])
async def test_pa44z_silence_switch_writes_dp16(pa44z, value):
    """Silence alarm switch writes DP 16 with the switch state."""
    tuya = pa44z.tuya_manufacturer
    with mock.patch.object(
        tuya.endpoint, "request", return_value=foundation.Status.SUCCESS
    ) as req:
        await tuya.write_attributes({"silence_alarm": value})
        await wait_for_zigpy_tasks()
    assert req.call_count == 1
    # Tuya payload: DP 16, type BOOL, length 1, value
    expected = b"\x10\x01\x00\x01" + bytes([value])
    assert req.call_args.kwargs["data"].endswith(expected)
