"""Tests for Tuya quirks."""

import asyncio
import contextlib
from unittest import mock

import pytest
from zigpy.zcl import foundation

import zhaquirks
import zhaquirks.tuya

zhaquirks.setup()


@pytest.mark.parametrize(
    "msg,attr_suffix,expected_power,expected_current,expected_volt",
    [
        (b"\t0\x02\x00\xd3\x06\x00\x00\x08\tn\x00\nA\x00\x01\xa6", "", 422, 2625, 2414),
        (b"\t2\x02\x00Z\x06\x00\x00\x08\ts\x00\n9\x00\x01\xa5", "", 421, 2617, 2419),
        (b"\t2\x02\x00Z\x06\x00\x00\x08\ts\x00\n9\x00\x91\xa5", "", -2037, 2617, 2419),
        (
            b"\t0\x02\x00\xd3\x07\x00\x00\x08\tn\x00\nA\x00\x01\xa6",
            "_ph_b",
            422,
            2625,
            2414,
        ),
        (
            b"\t2\x02\x00Z\x07\x00\x00\x08\ts\x00\n9\x00\x01\xa5",
            "_ph_b",
            421,
            2617,
            2419,
        ),
        (
            b"\t0\x02\x00\xd3\x08\x00\x00\x08\tn\x00\nA\x00\x01\xa6",
            "_ph_c",
            422,
            2625,
            2414,
        ),
        (
            b"\t2\x02\x00Z\x08\x00\x00\x08\ts\x00\n9\x00\x01\xa5",
            "_ph_c",
            421,
            2617,
            2419,
        ),
    ],
)
async def test_ts0601_electrical_measurement_multi_dp_converter(
    zigpy_device_from_v2_quirk,
    msg,
    attr_suffix,
    expected_power,
    expected_current,
    expected_volt,
):
    """Test converter for multiple electrical attributes mapped to the same tuya datapoint."""

    quirked = zigpy_device_from_v2_quirk("_TZE200_nslr42tt", "TS0601")
    ep = quirked.endpoints[1]

    tuya_manufacturer = ep.tuya_manufacturer
    hdr, data = tuya_manufacturer.deserialize(msg)
    status = tuya_manufacturer.handle_get_data(data.data)
    assert status == foundation.Status.SUCCESS

    electrical_meas_cluster = ep.electrical_measurement
    assert electrical_meas_cluster.get("active_power" + attr_suffix) == expected_power
    assert electrical_meas_cluster.get("rms_current" + attr_suffix) == expected_current
    assert electrical_meas_cluster.get("rms_voltage" + attr_suffix) == expected_volt


@pytest.mark.parametrize(
    "msg,expected_power",
    [
        (b"\x19\x8a\x02\x00\x0f\t\x02\x00\x04\x00\x00\x00\x80", 128),
        (b"\x19\x8a\x02\x00\x0f\t\x02\x00\x04\x19\x99\x99\x00", -156),
    ],
)
async def test_ts0601_power_converter(zigpy_device_from_v2_quirk, msg, expected_power):
    """Test converter for power."""

    quirked = zigpy_device_from_v2_quirk("_TZE200_nslr42tt", "TS0601")
    ep = quirked.endpoints[1]

    tuya_manufacturer = ep.tuya_manufacturer
    hdr, data = tuya_manufacturer.deserialize(msg)
    status = tuya_manufacturer.handle_get_data(data.data)
    assert status == foundation.Status.SUCCESS

    assert tuya_manufacturer.get("power") == expected_power


async def test_zm6lt1_phase_dp_converter(zigpy_device_from_v2_quirk):
    """Test the packed DP 6 phase converter of the Moes ZM6LT1."""

    quirked = zigpy_device_from_v2_quirk("_TZE284_2fnssffc", "TS0601")
    ep = quirked.endpoints[1]

    # real device capture: 234.9 V, 0.173 A, 16 W, 37 var, 40 VA, PF 39 %
    msg = (
        b"\x09\x18\x02\x00\x78\x06\x00\x00\x12"
        b"\x02\x0f\x09\x2d\x00\x00\xad\x00\x00\x10\x00\x00\x25\x00\x00\x28\x27\x00"
    )

    tuya_manufacturer = ep.tuya_manufacturer
    hdr, data = tuya_manufacturer.deserialize(msg)
    status = tuya_manufacturer.handle_get_data(data.data)
    assert status == foundation.Status.SUCCESS

    electrical_meas_cluster = ep.electrical_measurement
    assert electrical_meas_cluster.get("rms_voltage") == 2349
    assert electrical_meas_cluster.get("rms_current") == 173
    assert electrical_meas_cluster.get("active_power") == 16
    assert electrical_meas_cluster.get("reactive_power") == 37
    assert electrical_meas_cluster.get("apparent_power") == 40
    assert electrical_meas_cluster.get("power_factor") == 39


async def test_zm6lt1_poll_loop(zigpy_device_from_v2_quirk):
    """Test the ZM6LT1 periodic data-query poll loop."""

    quirked = zigpy_device_from_v2_quirk("_TZE284_2fnssffc", "TS0601")
    cluster = quirked.endpoints[1].tuya_manufacturer

    # instantiating the cluster inside a running loop starts the poller
    assert cluster._poll_task is not None
    cluster._poll_task.cancel()

    calls = []

    async def fake_command(command_id, expect_reply=True):
        calls.append(command_id)
        if len(calls) == 1:
            # first poll fails (e.g. radio not ready), the loop must retry
            raise RuntimeError("ApplicationController is not running")
        raise asyncio.CancelledError

    with (
        mock.patch.object(type(cluster), "POLL_INTERVAL", 0),
        mock.patch.object(cluster, "command", fake_command),
        pytest.raises(asyncio.CancelledError),
    ):
        await cluster._poll_loop()

    assert calls == [zhaquirks.tuya.TUYA_QUERY_DATA] * 2


async def test_zm6lt1_poller_replaced_on_new_cluster(zigpy_device_from_v2_quirk):
    """Test that re-instantiating the cluster cancels the previous poller."""

    quirked = zigpy_device_from_v2_quirk("_TZE284_2fnssffc", "TS0601")
    cluster = quirked.endpoints[1].tuya_manufacturer
    first_task = cluster._poll_task
    assert first_task is not None

    new_cluster = type(cluster)(cluster.endpoint)
    with contextlib.suppress(asyncio.CancelledError):
        await first_task
    assert first_task.cancelled()

    new_cluster._poll_task.cancel()


def test_zm6lt1_no_poller_without_event_loop(zigpy_device_from_v2_quirk):
    """Test that no poller is started when there is no running event loop."""

    quirked = zigpy_device_from_v2_quirk("_TZE284_2fnssffc", "TS0601")
    cluster = quirked.endpoints[1].tuya_manufacturer
    assert cluster._poll_task is None
