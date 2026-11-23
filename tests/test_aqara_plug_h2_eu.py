"""Tests for the Aqara Power Plug H2 EU (RGB) quirk (lumi.plug.aeu005)."""

import asyncio
from unittest import mock

from zigpy.zcl import ClusterType
from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement
from zigpy.zcl.clusters.smartenergy import Metering

import zhaquirks
from zhaquirks.xiaomi.aqara import aqara_plug_h2_eu
from zhaquirks.xiaomi.aqara.aqara_plug_h2_eu import AqaraH2PlugElectricalMeasurement

zhaquirks.setup()

EM = ElectricalMeasurement.AttributeDefs
SUMM = Metering.AttributeDefs.current_summ_delivered.id


def _device(zigpy_device_from_v2_quirk):
    device = zigpy_device_from_v2_quirk(
        "Aqara",
        "lumi.plug.aeu005",
        cluster_ids={
            1: {
                ElectricalMeasurement.cluster_id: ClusterType.Server,
                Metering.cluster_id: ClusterType.Server,
            }
        },
    )
    ep = device.endpoints[1]
    return ep.electrical_measurement, ep.smartenergy_metering


def test_quirk_applies(zigpy_device_from_v2_quirk):
    """The quirk replaces the ElectricalMeasurement cluster."""
    em, _ = _device(zigpy_device_from_v2_quirk)
    assert isinstance(em, AqaraH2PlugElectricalMeasurement)


async def test_ac_power_scaling_is_pinned(zigpy_device_from_v2_quirk):
    """Multiplier and divisor read as 1, regardless of what the device says."""
    em, _ = _device(zigpy_device_from_v2_quirk)

    success, fail = await em.read_attributes(
        [EM.ac_power_multiplier.id, EM.ac_power_divisor.id]
    )

    assert not fail
    assert success[EM.ac_power_multiplier.id] == 1
    assert success[EM.ac_power_divisor.id] == 1


async def test_power_update_refreshes_summation(zigpy_device_from_v2_quirk):
    """An active_power update triggers a read of current_summ_delivered."""
    em, metering = _device(zigpy_device_from_v2_quirk)

    with mock.patch.object(
        metering, "read_attributes", mock.AsyncMock(return_value=({}, {}))
    ) as read:
        em._update_attribute(EM.active_power.id, 982)
        await asyncio.sleep(0)

    read.assert_awaited_once_with([SUMM])


async def test_summation_refresh_is_throttled(zigpy_device_from_v2_quirk):
    """Updates within the refresh interval do not read again."""
    em, metering = _device(zigpy_device_from_v2_quirk)

    with (
        mock.patch.object(
            metering, "read_attributes", mock.AsyncMock(return_value=({}, {}))
        ) as read,
        mock.patch.object(aqara_plug_h2_eu.time, "monotonic") as monotonic,
    ):
        monotonic.return_value = 1000.0
        em._update_attribute(EM.active_power.id, 982)
        await asyncio.sleep(0)

        monotonic.return_value = 1030.0  # 30 s later: throttled
        em._update_attribute(EM.active_power.id, 982)
        await asyncio.sleep(0)
        assert read.await_count == 1

        monotonic.return_value = 1061.0  # past the interval: read again
        em._update_attribute(EM.active_power.id, 982)
        await asyncio.sleep(0)
        assert read.await_count == 2


async def test_other_attributes_do_not_refresh(zigpy_device_from_v2_quirk):
    """Only active_power updates trigger the refresh."""
    em, metering = _device(zigpy_device_from_v2_quirk)

    with mock.patch.object(
        metering, "read_attributes", mock.AsyncMock(return_value=({}, {}))
    ) as read:
        em._update_attribute(EM.rms_voltage.id, 230)
        await asyncio.sleep(0)

    read.assert_not_awaited()


async def test_failed_refresh_is_swallowed(zigpy_device_from_v2_quirk):
    """A failing read does not raise out of the background task."""
    em, metering = _device(zigpy_device_from_v2_quirk)

    with mock.patch.object(
        metering, "read_attributes", mock.AsyncMock(side_effect=asyncio.TimeoutError)
    ):
        em._update_attribute(EM.active_power.id, 982)
        await asyncio.sleep(0)

    assert em._summation_task.done()
    assert em._summation_task.exception() is None


async def test_no_new_refresh_while_previous_is_pending(zigpy_device_from_v2_quirk):
    """A refresh still in flight blocks a new one, even past the interval."""
    em, metering = _device(zigpy_device_from_v2_quirk)
    release = asyncio.Event()

    async def slow_read(*args, **kwargs):
        await release.wait()
        return {}, {}

    with (
        mock.patch.object(
            metering, "read_attributes", mock.AsyncMock(side_effect=slow_read)
        ) as read,
        mock.patch.object(aqara_plug_h2_eu.time, "monotonic") as monotonic,
    ):
        monotonic.return_value = 1000.0
        em._update_attribute(EM.active_power.id, 982)
        await asyncio.sleep(0)

        monotonic.return_value = 2000.0  # well past the interval, but still pending
        em._update_attribute(EM.active_power.id, 982)
        await asyncio.sleep(0)
        assert read.await_count == 1

        release.set()
        await em._summation_task
