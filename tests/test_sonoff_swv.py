"""Tests for the Sonoff SWV quirk."""

from unittest.mock import AsyncMock

import pytest
from zigpy.zcl.clusters.general import OnOff

from zhaquirks.sonoff.swv import SonoffSWVOnOffCluster, SonoffSWVTimerCluster


async def test_swv_on_off_cluster(zigpy_device_from_v2_quirk):
    """Test that the SWV uses the custom OnOff cluster."""

    device = zigpy_device_from_v2_quirk("SONOFF", "SWV")

    on_off_cluster = device.endpoints[1].in_clusters[OnOff.cluster_id]

    assert isinstance(on_off_cluster, SonoffSWVOnOffCluster)


async def test_start_timed_watering(zigpy_device_from_v2_quirk):
    """Test starting timed watering."""

    device = zigpy_device_from_v2_quirk("SONOFF", "SWV")
    on_off_cluster = device.endpoints[1].in_clusters[OnOff.cluster_id]

    on_off_cluster.on_with_timed_off = AsyncMock()

    await on_off_cluster.start_timed_watering(60)

    on_off_cluster.on_with_timed_off.assert_awaited_once_with(
        on_off_control=OnOff.OnOffControl(0),
        on_time=60,
        off_wait_time=0,
    )


async def test_swv_timer_cluster(zigpy_device_from_v2_quirk):
    """Test that the SWV has the local timer cluster."""

    device = zigpy_device_from_v2_quirk("SONOFF", "SWV")

    timer_cluster = device.endpoints[1].in_clusters[SonoffSWVTimerCluster.cluster_id]

    assert isinstance(timer_cluster, SonoffSWVTimerCluster)

    await timer_cluster.write_attributes(
        {
            SonoffSWVTimerCluster.AttributeDefs.watering_duration.name: 120,
        }
    )
    assert (
        timer_cluster.get(SonoffSWVTimerCluster.AttributeDefs.watering_duration.id)
        == 120
    )


async def test_timer_cluster_starts_timed_watering(
    zigpy_device_from_v2_quirk,
):
    """Test starting timed watering with the configured duration."""

    device = zigpy_device_from_v2_quirk("SONOFF", "SWV")

    timer_cluster = device.endpoints[1].in_clusters[SonoffSWVTimerCluster.cluster_id]
    on_off_cluster = device.endpoints[1].in_clusters[OnOff.cluster_id]

    on_off_cluster.start_timed_watering = AsyncMock()

    await timer_cluster.write_attributes(
        {
            SonoffSWVTimerCluster.AttributeDefs.watering_duration.name: 120,
        }
    )

    await timer_cluster.start_timed_watering()

    on_off_cluster.start_timed_watering.assert_awaited_once_with(120)


async def test_start_timed_watering_without_duration(
    zigpy_device_from_v2_quirk,
):
    """Test that timed watering requires a configured duration."""

    device = zigpy_device_from_v2_quirk("SONOFF", "SWV")

    timer_cluster = device.endpoints[1].in_clusters[SonoffSWVTimerCluster.cluster_id]
    on_off_cluster = device.endpoints[1].in_clusters[OnOff.cluster_id]

    on_off_cluster.start_timed_watering = AsyncMock()

    with pytest.raises(ValueError, match="Watering duration is not configured."):
        await timer_cluster.start_timed_watering()

    on_off_cluster.start_timed_watering.assert_not_awaited()


@pytest.mark.parametrize("duration", [0, 0xFFFF])
async def test_start_timed_watering_rejects_invalid_duration(
    zigpy_device_from_v2_quirk, duration
):
    """Test that invalid watering durations are rejected."""

    device = zigpy_device_from_v2_quirk("SONOFF", "SWV")
    on_off_cluster = device.endpoints[1].in_clusters[OnOff.cluster_id]
    on_off_cluster.on_with_timed_off = AsyncMock()

    with pytest.raises(
        ValueError, match="Watering duration must be between 1 and 65534 seconds"
    ):
        await on_off_cluster.start_timed_watering(duration)

    on_off_cluster.on_with_timed_off.assert_not_awaited()


@pytest.mark.parametrize("duration", [1, 0xFFFE])
async def test_start_timed_watering_accepts_boundary_duration(
    zigpy_device_from_v2_quirk, duration
):
    """Test valid watering duration boundaries."""

    device = zigpy_device_from_v2_quirk("SONOFF", "SWV")

    on_off_cluster = device.endpoints[1].in_clusters[OnOff.cluster_id]
    on_off_cluster.on_with_timed_off = AsyncMock()

    await on_off_cluster.start_timed_watering(duration)

    on_off_cluster.on_with_timed_off.assert_awaited_once_with(
        on_off_control=OnOff.OnOffControl(0),
        on_time=duration,
        off_wait_time=0,
    )
